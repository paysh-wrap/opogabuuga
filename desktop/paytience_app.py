"""Paytience desktop entry point (packaged with PyInstaller into Paytience.exe / Paytience.app).

Nothing to install: Python, the backend and the built dashboard are inside the executable. On first run it creates
your keys (.env), the database and your login, then opens the dashboard in your browser. TradingAgents and
Vibe-Trading are downloaded into their own folders on first run (internet needed once); until then the bias is
NO_TRADE and nothing trades.
All user data lives next to the executable in ./paytience-data (keys, database, logs)."""

from __future__ import annotations

import json
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
URL = "http://127.0.0.1:8000"  # health checks (always loopback)


def ui_url() -> str:
    """D103: every build opens under its OWN browser origin (paytience-<commit7>.localhost). *.localhost always resolves to this
    PC, but the browser treats each name as a different site, so an old build's cached page / service worker can never
    serve a blank or stale interface for a new build. Dev builds keep 127.0.0.1."""
    try:
        from app.updater import load_version

        v = load_version()
        if v.commit and v.commit != "dev":
            stamp = "".join(ch for ch in v.built_at if ch.isdigit())[:12]  # rebuilds of one commit get a new name too
            return f"http://paytience-{v.commit[:7]}{'-' + stamp if stamp else ''}.localhost:8000"
    except Exception:  # noqa: BLE001 - never block startup on a name
        return URL
    return URL
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
    os.environ["PAYTIENCE_TR1_ROOT"] = str(DATA)  # D94: optional .venv-tr1 + TR1_HOME under paytience-data
    os.environ["PAYTIENCE_TOOLS_DIR"] = str(DATA / "tools")  # D79: ngrok / cloudflared live in their own folder
    os.environ["PAYTIENCE_VERSION_FILE"] = str(BUNDLE / "desktop" / "version.json")  # D88: commit + build time
    if FROZEN:  # D88: auto-update only for the packaged app; paytience-data is never touched by an update
        os.environ["PAYTIENCE_APP_DIR"] = str(EXE_DIR)
        os.environ["PAYTIENCE_UPDATES_DIR"] = str(DATA / "updates")
        (DATA / "updates").mkdir(exist_ok=True)
    os.environ["PAYTIENCE_TUNNEL_AUTOSTART"] = "true"  # ngrok static domain if saved, else Cloudflare quick tunnel + warning


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
        reset = DATA / "reset-password.txt"
        existing = s.query(User).filter(User.username == USERNAME).one_or_none()
        if existing is not None and not reset.exists():
            return
        if existing is not None:  # forgot password: drop a file named reset-password.txt in paytience-data
            say("Password reset requested — choose a NEW password for PayDay.")
        if existing is None:
            say(f"Create your dashboard login (user name: {USERNAME}). Choose a strong password.")
        import getpass

        pw = os.environ.pop("PAYTIENCE_ADMIN_PASSWORD", "")  # automated setups/tests; otherwise ask
        while not pw:
            pw = getpass.getpass("Password: ")
            if len(pw) < 8 or pw != getpass.getpass("Repeat password: "):
                print("  Passwords must match and be at least 8 characters.")
                pw = ""
        if existing is not None:
            from app.auth import hash_password

            existing.password_hash = hash_password(pw)
            reset.unlink(missing_ok=True)
        else:
            create_user(s, USERNAME, pw)
        s.commit()


def _run(cmd: list[str]) -> None:
    """Run a helper command with a clean environment (the frozen app's PYTHON* vars break child Pythons) and
    surface its real error text instead of a bare CalledProcessError."""
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("PYTHON", "VIRTUAL_ENV", "_MEI", "PIP_"))}
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode:
        raise RuntimeError(f"{' '.join(cmd[:4])}… exit {r.returncode}: {(r.stderr or r.stdout).strip()[-600:]}")


def _python_for_venv() -> list[str]:
    """A real Python to build helper venvs with: the system one if present, else uv (downloads one)."""
    uv = DATA / ("uv.exe" if WIN else "uv")
    if not uv.exists():
        say("Fetching a private Python runtime (one time)…")
        if WIN:  # plain download of uv.exe (no PowerShell: blocked/odd paths made that fail)
            import io
            import zipfile
            DATA.mkdir(parents=True, exist_ok=True)
            url = "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip"
            with urllib.request.urlopen(url, timeout=180) as r:
                z = zipfile.ZipFile(io.BytesIO(r.read()))
            uv.write_bytes(z.read("uv.exe"))
        else:
            _run(["sh", "-c", f"curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR='{DATA}' sh"])
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
                _run([py[0], "venv", "--python", "3.12", str(path)])
            else:
                _run([*py, "-m", "venv", str(path)])

        def pip(path: Path, *args: str) -> None:
            vpy = path / ("Scripts/python.exe" if WIN else "bin/python")
            if use_uv:
                _run([py[0], "pip", "install", "--python", str(vpy), "-q", *args])
            else:
                _run([str(vpy), "-m", "pip", "install", "-q", *args])

        if not ta_py.exists():
            say("Installing TradingAgents (the AI daily bias) — a few minutes, one time…")
            src = DATA / "TradingAgents-src"
            if not src.exists():
                url = f"https://github.com/TauricResearch/TradingAgents/archive/{TA_COMMIT}.zip"  # exact pinned commit
                with urllib.request.urlopen(url, timeout=120) as r:
                    zipfile.ZipFile(io.BytesIO(r.read())).extractall(DATA)
                shutil.move(str(DATA / f"TradingAgents-{TA_COMMIT}"), str(src))
            shutil.rmtree(DATA / ".venv-ta", ignore_errors=True)  # a half-built venv from a failed try would be skipped forever
            try:
                venv(DATA / ".venv-ta")
                pip(DATA / ".venv-ta", str(src))
            except Exception:
                shutil.rmtree(DATA / ".venv-ta", ignore_errors=True)
                raise
        if not vt_exe.exists():
            say("Installing Vibe-Trading (second AI opinion)…")
            shutil.rmtree(DATA / ".venv-vt", ignore_errors=True)
            try:
                venv(DATA / ".venv-vt")
                pip(DATA / ".venv-vt", VT_PIN)
            except Exception:
                shutil.rmtree(DATA / ".venv-vt", ignore_errors=True)
                raise
    except Exception as e:  # noqa: BLE001 - optional tools; the app still runs
        print(f"  ⚠ AI tools not installed yet ({type(e).__name__}: {e}). The app runs; no trades until they install. "
              "Close and reopen Paytience later to retry.")


PORT = 8000
RUN_DIR = DATA / "run"
TOKEN_FILE = RUN_DIR / "shutdown.token"


def free_port_or_exit() -> None:
    """D97: never let an OLD Paytience keep serving :8000 (stale UI/server). Retire a verified old Paytience, else stop."""
    from app.portguard import PortBusy, ensure_port_free

    try:
        ensure_port_free(PORT, TOKEN_FILE, say=say)
    except PortBusy as e:
        msg = str(e)
        print(f"\n✗ {msg}", flush=True)
        if WIN:  # the console may be hidden/closing: also show a window
            try:
                import ctypes

                ctypes.windll.user32.MessageBoxW(0, msg, "Paytience", 0x10)  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001 - the printed message is enough
                pass
        sys.exit(2)


def publish_shutdown_token() -> None:
    """Per-process secret that lets a NEWER Paytience ask this one to exit (local-only endpoint). Written only after
    the port guard ran, so we never overwrite the token of the process we are about to retire."""
    from app.buildinfo import SHUTDOWN_TOKEN_ENV

    token = secrets.token_urlsafe(32)
    os.environ[SHUTDOWN_TOKEN_ENV] = token
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(token, encoding="utf-8")


def serve(host: str) -> None:
    import uvicorn

    from app.main import create_app

    say(f"Paytience is running — open {ui_url()}  (PAPER mode — close this window to stop)")
    app = create_app()
    server = uvicorn.Server(uvicorn.Config(app, host=host, port=PORT, log_level="warning"))
    app.state.request_shutdown = lambda: setattr(server, "should_exit", True)  # graceful exit for /api/system/shutdown
    try:
        server.run()
    except SystemExit:  # uvicorn exits with 1 when it cannot bind: say so instead of a vanishing window
        print(f"\n✗ Paytience could not open port {PORT}. Close the program using it and start Paytience again.", flush=True)
        raise
    finally:
        TOKEN_FILE.unlink(missing_ok=True)


def main() -> None:
    sys.path.insert(0, str(BUNDLE / "backend"))
    os.chdir(BUNDLE / "backend")
    ensure_env()
    free_port_or_exit()  # before the DB is touched and before uvicorn binds
    publish_shutdown_token()
    migrate()
    ensure_login()
    ensure_ai_tools()
    # Always reachable from your own devices (phone app on the same Wi-Fi or via Tailscale); login still required.
    host = "0.0.0.0"
    addrs = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            addrs.add(info[4][0])
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sk:
            sk.connect(("192.0.2.1", 80))
            addrs.add(sk.getsockname()[0])
    except OSError:
        pass
    ts = sorted(a for a in addrs if a.startswith("100."))  # Tailscale addresses are 100.x.x.x
    lan = sorted(a for a in addrs if not a.startswith(("127.", "100.")))
    if ts:
        say(f"PHONE (Tailscale, works on mobile data): http://{ts[0]}:8000")
    else:
        say("PHONE via Tailscale: Tailscale not detected on this computer — install it and sign in, then restart.")
    for a in lan:
        print(f"  PHONE (same Wi-Fi): http://{a}:8000")
    print("  If the phone can't connect: allow Paytience in the Windows firewall prompt (Private + Public).")

    def open_when_ready() -> None:
        for _ in range(120):
            try:
                with urllib.request.urlopen(URL + "/api/health", timeout=1) as r:
                    h = json.loads(r.read().decode("utf-8"))
                if h.get("pid") != os.getpid():  # D97: an OLD server answering is not "ready" — never open its UI
                    raise RuntimeError("health answered by another process")
                if FROZEN:  # D88: tell a pending update the new version started; drop backups (old-*)
                    from app.updater import on_healthy_start

                    try:
                        failed = on_healthy_start(DATA / "updates", str((h.get("build") or {}).get("commit", "")))
                        if failed:
                            print(f"  ⚠ {failed}")
                    except OSError as e:
                        print(f"  ⚠ Update bookkeeping failed: {e}")
                webbrowser.open(ui_url())
                return
            except Exception:  # noqa: BLE001 - still starting
                time.sleep(1)

    free_port_or_exit()  # again: the AI-tool install above can take minutes
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
