#!/usr/bin/env python3
"""Paytience one-click launcher (Mac / Windows / Linux). Needs only Python 3.11+ and Node 18+ installed.

First run: installs everything, creates your secret keys (.env), sets up the database, asks once for your dashboard
password, installs TradingAgents, builds the UI. Every run: starts the app and opens http://127.0.0.1:8000.
Usage:  python3 start.py            (or double-click start.command on Mac / start.bat on Windows)
        python3 start.py --no-browser
        python3 start.py --phone        (also reachable from your phone on the same Wi-Fi → install as an app)
Uses only the Python standard library. Never stores your password (only its hash, in the local database)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND, FRONTEND = ROOT / "backend", ROOT / "frontend"
WIN = os.name == "nt"
VPY = ROOT / ".venv" / ("Scripts/python.exe" if WIN else "bin/python")
TA_PY = ROOT / ".venv-ta" / ("Scripts/python.exe" if WIN else "bin/python")
TA_TAG, TA_COMMIT = "v0.7.1", "3e44faafa042daf953f6ec2422ae36bb1fd4f50f"  # same pin as the Makefile
URL = "http://127.0.0.1:8000"
USERNAME = "PayDay"


def say(msg: str) -> None:
    print(f"\n▶ {msg}", flush=True)


def run(cmd: list[str], cwd: Path = ROOT, **kw: object) -> None:
    subprocess.run(cmd, cwd=cwd, check=True, **kw)  # type: ignore[call-overload]


def need(tool: str, url: str) -> str:
    path = shutil.which(tool)
    if not path:
        sys.exit(f"✗ {tool} is not installed. Install it from {url} and run this again.")
    return path


def main() -> None:
    if sys.version_info < (3, 11):
        sys.exit("✗ Python 3.11 or newer is needed: https://www.python.org/downloads/")
    npm = need("npm", "https://nodejs.org (LTS)")

    if not VPY.exists():
        say("Installing the app (first run only, a few minutes)…")
        run([sys.executable, "-m", "venv", ".venv"])
        run([str(VPY), "-m", "pip", "install", "-q", "--upgrade", "pip"])
        run([str(VPY), "-m", "pip", "install", "-q", "-e", "backend"])

    if not (FRONTEND / "node_modules").exists():
        say("Installing the dashboard…")
        run([npm, "ci", "--no-audit", "--no-fund"], cwd=FRONTEND)
    dist = FRONTEND / "dist" / "index.html"
    newest_src = max((p.stat().st_mtime for p in (FRONTEND / "src").rglob("*") if p.is_file()), default=0)
    if not dist.exists() or dist.stat().st_mtime < newest_src:
        say("Building the dashboard…")
        run([npm, "run", "build"], cwd=FRONTEND)

    env_file = ROOT / ".env"
    if not env_file.exists():
        say("Creating your secret keys (.env — keep this file private, never share it)…")
        keys = subprocess.run([str(VPY), "-m", "app.cli", "keys"], cwd=BACKEND, check=True, capture_output=True,
                              text=True).stdout
        example = (ROOT / ".env.example").read_text(encoding="utf-8")
        lines = [ln for ln in example.splitlines() if not ln.startswith(("PAYTIENCE_MASTER_KEY=", "PAYTIENCE_WEBHOOK_SECRET="))]
        env_file.write_text("\n".join(lines) + "\n" + keys, encoding="utf-8")

    (ROOT / "data").mkdir(exist_ok=True)
    say("Updating the database…")
    run([str(VPY), "-m", "alembic", "upgrade", "head"], cwd=BACKEND, stdout=subprocess.DEVNULL)

    has_user = subprocess.run(
        [str(VPY), "-c", "from app.db import make_engine; from app.settings import get_settings; from app.models import User;"
         "from sqlalchemy.orm import Session; e=make_engine(get_settings().database_url);"
         "s=Session(e); print(s.query(User).count())"],
        cwd=BACKEND, capture_output=True, text=True,
    ).stdout.strip()
    if has_user in ("", "0"):
        say(f"Create your dashboard login (user name: {USERNAME}). Choose a strong password:")
        run([str(VPY), "-m", "app.cli", "create-admin", USERNAME], cwd=BACKEND)

    if not TA_PY.exists() and shutil.which("git"):
        say("Installing TradingAgents (the AI daily bias)…")
        vendor = ROOT / "vendor" / "TradingAgents"
        if not vendor.exists():
            run(["git", "clone", "-q", "--depth", "1", "--branch", TA_TAG,
                 "https://github.com/TauricResearch/TradingAgents.git", str(vendor)])
        head = subprocess.run(["git", "-C", str(vendor), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        if head != TA_COMMIT:
            print("  ⚠ TradingAgents commit does not match the pinned version — skipped (bias = NO_TRADE).")
        else:
            run([sys.executable, "-m", "venv", ".venv-ta"])
            run([str(TA_PY), "-m", "pip", "install", "-q", str(vendor)])
    elif not TA_PY.exists():
        print("  ⚠ git not found: TradingAgents not installed — the app runs but takes no trades (bias = NO_TRADE).")

    host = "127.0.0.1"
    if "--phone" in sys.argv:  # same Wi-Fi only; the dashboard still needs your login
        import socket

        host = "0.0.0.0"
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sk:
                sk.connect(("192.0.2.1", 80))  # no packet is sent; picks the Wi-Fi address
                lan = sk.getsockname()[0]
        except OSError:
            lan = "<this computer's IP>"
        say(f"PHONE: on the same Wi-Fi open http://{lan}:8000 → sign in → Share/⋮ menu → 'Add to Home Screen'.")
        print("  Only use this on your own home Wi-Fi. Away from home use a Cloudflare Tunnel (README).")
    say(f"Starting Paytience on {URL}  (PAPER mode by default — press Ctrl+C to stop)")
    if "--no-browser" not in sys.argv:
        def open_when_ready() -> None:
            for _ in range(120):
                try:
                    urllib.request.urlopen(URL + "/api/health", timeout=1)
                    webbrowser.open(URL)
                    return
                except Exception:  # noqa: BLE001 - server still starting
                    time.sleep(1)
        threading.Thread(target=open_when_ready, daemon=True).start()
    try:  # the server's own exit (Ctrl+C / closed window) is not a setup failure
        subprocess.run([str(VPY), "-m", "uvicorn", "app.main:create_app", "--factory", "--host", host,
                        "--port", "8000"], cwd=BACKEND)
    except KeyboardInterrupt:
        pass
    print("\nPaytience stopped. Run start again any time.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        sys.exit(f"✗ A setup step failed ({' '.join(map(str, e.cmd))[:120]}). Fix the message above and run again.")
