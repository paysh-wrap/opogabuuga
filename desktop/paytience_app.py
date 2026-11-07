"""Paytience desktop entry point (packaged with PyInstaller into Paytience.exe / Paytience.app).

Nothing to install: Python, the backend and the built dashboard are inside the executable. On first run it creates
your keys (.env), the database and your login, then opens the dashboard in your browser. TradingAgents and
Vibe-Trading are downloaded into their own folders on first run (internet needed once); until then the bias is
NO_TRADE and nothing trades.
All user data lives next to the executable in ./paytience-data (keys, database, logs)."""

from __future__ import annotations

import os
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
BUNDLE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))  # repo root when not frozen
EXE_DIR = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parents[1]
DATA = EXE_DIR / "paytience-data"
URL = "http://127.0.0.1:8000"
USERNAME = "PayDay"
TA_TAG, TA_COMMIT = "v0.7.1", "3e44faafa042daf953f6ec2422ae36bb1fd4f50f"
VT_PIN = "vibe-trading-ai[anthropic]==0.1.19"
WIN = os.name == "nt"


def say(msg: str) -> None:
    print(f"\n▶ {msg}", flush=True)


def ensure_env() -> None:
    DATA.mkdir(exist_ok=True)
    env_file = DATA / ".env"
    if not env_file.exists():
        say("Creating your secret keys (paytience-data/.env — keep this folder private)…")
        from app.crypto import new_master_key

        env_file.write_text(
            f"PAYTIENCE_MASTER_KEY={new_master_key()}\nPAYTIENCE_WEBHOOK_SECRET={secrets.token_urlsafe(32)}\n"
            "PAYTIENCE_ALLOW_LIVE=false\nPAYTIENCE_COOKIE_SECURE=false\n",
            encoding="utf-8",
        )
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
    os.environ["PAYTIENCE_DATABASE_URL"] = f"sqlite:///{(DATA / 'paytience.db').as_posix()}"
    os.environ["PAYTIENCE_WEB_DIST"] = str(BUNDLE / "frontend" / "dist")
    os.environ["PAYTIENCE_RULES_PATH"] = str(BUNDLE / "config" / "rules" / "lucid_flex_25k.yaml")
    os.environ["PAYTIENCE_TA_PYTHON"] = str(DATA / ".venv-ta" / ("Scripts/python.exe" if WIN else "bin/python"))
    os.environ["PAYTIENCE_VT_ROOT"] = str(DATA)


def migrate() -> None:
    say("Updating the database…")
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BUNDLE / "backend" / "alembic.ini"))
    cfg.set_main_option("script_location", str(BUNDLE / "backend" / "alembic"))
    cfg.set_main_option("sqlalchemy.url", os.environ["PAYTIENCE_DATABASE_URL"])
    command.upgrade(cfg, "head")


def ensure_login() -> None:
    from sqlalchemy.orm import Session

    from app.auth import create_user
    from app.db import make_engine
    from app.models import User

    with Session(make_engine(os.environ["PAYTIENCE_DATABASE_URL"])) as s:
        if s.query(User).count():
            return
        say(f"Create your dashboard login (user name: {USERNAME}). Choose a strong password.")
        import getpass

        pw = os.environ.pop("PAYTIENCE_ADMIN_PASSWORD", "")  # automated setups/tests; otherwise ask
        while not pw:
            pw = getpass.getpass("Password: ")
            if len(pw) < 8 or pw != getpass.getpass("Repeat password: "):
                print("  Passwords must match and be at least 8 characters.")
                pw = ""
        create_user(s, USERNAME, pw)
        s.commit()


def _python_for_venv() -> list[str]:
    """A real Python to build helper venvs with: the system one if present, else uv (downloads one)."""
    for cand in ("python3.12", "python3.11", "python3", "python", "py"):
        p = __import__("shutil").which(cand)
        if p:
            try:
                out = subprocess.run([p, "-c", "import sys;print(sys.version_info>=(3,11))"], capture_output=True, text=True, timeout=20).stdout
                if out.strip() == "True":
                    return [p]
            except Exception:  # noqa: BLE001 - try the next candidate
                pass
    uv = DATA / ("uv.exe" if WIN else "uv")
    if not uv.exists():
        say("Fetching a private Python runtime (one time)…")
        if WIN:
            subprocess.run(["powershell", "-NoProfile", "-Command",
                            f"irm https://astral.sh/uv/install.ps1 | iex; Copy-Item \"$env:USERPROFILE\\.local\\bin\\uv.exe\" \"{uv}\""], check=True)
        else:
            subprocess.run(["sh", "-c", f"curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR='{DATA}' sh"], check=True)
    return [str(uv)]  # uv creates the venvs and installs into them


def ensure_ai_tools() -> None:
    """TradingAgents (pinned commit, source archive — no git needed) + Vibe-Trading, each in its own venv under
    paytience-data. Failures never stop the app: the bias is simply NO_TRADE until they are installed."""
    import io
    import shutil
    import zipfile

    ta_py = Path(os.environ["PAYTIENCE_TA_PYTHON"])
    vt_exe = DATA / ".venv-vt" / ("Scripts/vibe-trading.exe" if WIN else "bin/vibe-trading")
    if ta_py.exists() and vt_exe.exists():
        return
    try:
        py = _python_for_venv()
        use_uv = py[0].endswith(("uv", "uv.exe"))

        def venv(path: Path) -> None:
            if use_uv:
                subprocess.run([py[0], "venv", "--python", "3.12", str(path)], check=True)
            else:
                subprocess.run([*py, "-m", "venv", str(path)], check=True)

        def pip(path: Path, *args: str) -> None:
            vpy = path / ("Scripts/python.exe" if WIN else "bin/python")
            if use_uv:
                subprocess.run([py[0], "pip", "install", "--python", str(vpy), "-q", *args], check=True)
            else:
                subprocess.run([str(vpy), "-m", "pip", "install", "-q", *args], check=True)

        if not ta_py.exists():
            say("Installing TradingAgents (the AI daily bias) — a few minutes, one time…")
            src = DATA / "TradingAgents-src"
            if not src.exists():
                url = f"https://github.com/TauricResearch/TradingAgents/archive/{TA_COMMIT}.zip"  # exact pinned commit
                with urllib.request.urlopen(url, timeout=120) as r:
                    zipfile.ZipFile(io.BytesIO(r.read())).extractall(DATA)
                shutil.move(str(DATA / f"TradingAgents-{TA_COMMIT}"), str(src))
            venv(DATA / ".venv-ta")
            pip(DATA / ".venv-ta", str(src))
        if not vt_exe.exists():
            say("Installing Vibe-Trading (second AI opinion)…")
            venv(DATA / ".venv-vt")
            pip(DATA / ".venv-vt", VT_PIN)
    except Exception as e:  # noqa: BLE001 - optional tools; the app still runs
        print(f"  ⚠ AI tools not installed yet ({type(e).__name__}). The app runs; no trades until they install. "
              "Close and reopen Paytience later to retry.")


def serve(host: str) -> None:
    import uvicorn

    from app.main import create_app

    say(f"Paytience is running at {URL}  (PAPER mode — close this window to stop)")
    uvicorn.run(create_app(), host=host, port=8000, log_level="warning")


def main() -> None:
    sys.path.insert(0, str(BUNDLE / "backend"))
    os.chdir(BUNDLE / "backend")
    ensure_env()
    migrate()
    ensure_login()
    ensure_ai_tools()
    host = "127.0.0.1"
    if "--phone" in sys.argv or (DATA / "phone-mode.txt").exists():
        host = "0.0.0.0"
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sk:
                sk.connect(("192.0.2.1", 80))
                lan = sk.getsockname()[0]
        except OSError:
            lan = "<this computer's IP>"
        say(f"PHONE: on the same Wi-Fi (or Tailscale) open http://{lan}:8000 in the Paytience phone app.")

    def open_when_ready() -> None:
        for _ in range(120):
            try:
                urllib.request.urlopen(URL + "/api/health", timeout=1)
                webbrowser.open(URL)
                return
            except Exception:  # noqa: BLE001 - still starting
                time.sleep(1)

    threading.Thread(target=open_when_ready, daemon=True).start()
    serve(host)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:  # noqa: BLE001 - show the error instead of a vanishing window
        print(f"\n✗ Paytience could not start: {type(e).__name__}: {e}")
        input("Press Enter to close…")
