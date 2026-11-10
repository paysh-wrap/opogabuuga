"""D88: desktop auto-update API. Install only on user click; blocked while positions are open or automation armed."""

from __future__ import annotations

import asyncio
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import audit, updater
from app.api.deps import Principal, current_user, get_db
from app.connections import service as conn
from app.crypto import MasterKeyMissing, Vault
from app.models import Account

router = APIRouter(prefix="/api/updates")
log = structlog.get_logger()
PID = "github_updates"


def _desktop() -> tuple[Path, Path] | None:
    app_dir, updates = os.environ.get("PAYTIENCE_APP_DIR"), os.environ.get("PAYTIENCE_UPDATES_DIR")
    return (Path(app_dir), Path(updates)) if app_dir and updates else None


def _token(request: Request, db: Session) -> str | None:
    try:
        vault = Vault(request.app.state.settings.master_key.get_secret_value())
    except MasterKeyMissing:
        return None
    creds = conn.credentials(db, vault, PID)
    return (creds or {}).get("token") or None


async def _blocked(request: Request, db: Session) -> str | None:
    c = request.app.state.controller
    try:
        positions = len(await c.open_positions(db))
    except Exception as e:  # unknown broker state = not safe to update
        return f"Could not read positions ({type(e).__name__}) — update blocked"
    armed = db.execute(select(func.count()).select_from(Account).where(Account.armed)).scalar_one()
    return updater.block_reason(positions, int(armed), str(c.mode))


def _fail(request: Request, title: str, detail: str) -> None:
    log.error("update.failed", title=title, detail=detail)
    request.app.state.controller.notify("error", title, detail, "update")
    request.app.state.update_last = {**getattr(request.app.state, "update_last", {}), "error": detail}


@router.get("")
async def status(
    request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    d = _desktop()
    failed = None
    if d and (d[1] / updater.FAILED_FLAG).exists():
        failed = (d[1] / updater.FAILED_FLAG).read_text(encoding="utf-8").strip()
    return {
        "version": updater.load_version().as_dict(),
        "desktop": d is not None,
        "token_set": _token(request, db) is not None,
        "last_check": getattr(request.app.state, "update_last", None),
        "failed_update": failed,
        "blocked": await _blocked(request, db),
    }


@router.post("/check")
async def check(
    request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    try:
        res = await updater.check(request.app.state.http, _token(request, db), updater.load_version())
    except updater.UpdateError as e:
        _fail(request, "Update check failed", str(e))
        raise HTTPException(502, str(e)) from e
    res["checked_at"] = request.app.state.clock.now().isoformat()
    request.app.state.update_last = res
    log.info("update.checked", available=res["available"], commit=res.get("commit"))
    return res


@router.post("/dismiss-failure")
def dismiss(_: Principal = Depends(current_user)) -> dict[str, bool]:
    d = _desktop()
    if d:
        (d[1] / updater.FAILED_FLAG).unlink(missing_ok=True)
    return {"ok": True}


def _launch(script: Path) -> None:  # pragma: no cover - Windows only
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen(["cmd", "/c", str(script)], creationflags=flags, close_fds=True)  # noqa: S603,S607 - our script
    asyncio.get_running_loop().call_later(2.0, os._exit, 0)


@router.post("/install")
async def install(
    request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    st = request.app.state
    d = _desktop()
    if d is None or (os.name != "nt" and not os.environ.get("PAYTIENCE_UPDATE_DRY_RUN")):
        raise HTTPException(409, "Installing updates only works in the Windows desktop app")
    app_dir, updates = d
    reason = await _blocked(request, db)
    if reason:
        raise HTTPException(409, reason)
    token = _token(request, db)
    if not token:
        raise HTTPException(409, "Add the GitHub (app updates) token on the Connections page first")
    try:
        res = await updater.check(st.http, token, updater.load_version())
        if not res["available"] or not res["asset"]:
            raise updater.UpdateError("No newer version available")
        log.info("update.download", commit=res["commit"], size=res["asset"].get("size"))
        zip_path = await updater.download(st.http, token, res["asset"], updates)
        log.info("update.verified", sha256_checked=res["asset"].get("digest") is not None)
        new_dir = updater.extract(zip_path, updates / "staging")
        backup = updates / f"old-{int(time.time())}"
        script = updates / "apply-update.bat"
        script.write_text(updater.updater_script(app_dir, new_dir, backup, updates, os.getpid()), encoding="utf-8")
        (updates / updater.FAILED_FLAG).unlink(missing_ok=True)
    except (updater.UpdateError, OSError) as e:
        _fail(request, "Update failed — old version kept", str(e))
        raise HTTPException(502, str(e)) from e
    audit.record(db, st.clock, p.user.username, "app.update_install", res["commit"] or "", {})
    db.commit()
    log.info("update.launching", script=str(script))
    if os.name == "nt":  # pragma: no cover
        _launch(script)
    return {"ok": True, "commit": res["commit"], "restarting": os.name == "nt"}
