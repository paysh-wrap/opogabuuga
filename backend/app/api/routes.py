"""REST routes for Phase 1 (+ D3 connections). Trading routes arrive in later phases."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import audit
from app.api.deps import Principal, current_user, get_db
from app.auth import CSRF_COOKIE, SESSION_COOKIE, authenticate, close_session, open_session
from app.connections import service as conn
from app.connections.registry import LLM_PROVIDERS, get_provider
from app.crypto import MasterKeyMissing, Vault

router = APIRouter(prefix="/api")


@router.get("/health")
def health(request: Request) -> dict[str, Any]:
    st = request.app.state
    return {
        "app": "paytience",
        "status": "ok",
        "time": st.clock.now().isoformat(),
        "mode": "LIVE" if st.settings.allow_live else "PAPER",
        "ws_clients": st.hub.count,
    }


# ---------- auth ----------
class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


@router.post("/auth/login")
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)) -> dict[str, Any]:
    st = request.app.state
    client = request.client.host if request.client else "?"
    if st.login_limiter.blocked(client):
        raise HTTPException(429, "too many failed attempts, wait a minute")
    user = authenticate(db, body.username, body.password)
    if user is None:
        st.login_limiter.fail(client)
        audit.record(db, st.clock, body.username[:64], "auth.login_failed", "", {"ip": client})
        db.commit()
        raise HTTPException(401, "invalid username or password")
    token, csrf = open_session(db, user, st.clock, st.settings.session_hours)
    audit.record(db, st.clock, user.username, "auth.login", "", {"ip": client})
    max_age = st.settings.session_hours * 3600
    secure = st.settings.cookie_secure
    response.set_cookie(SESSION_COOKIE, token, max_age=max_age, httponly=True, samesite="strict", secure=secure)
    response.set_cookie(CSRF_COOKIE, csrf, max_age=max_age, httponly=False, samesite="strict", secure=secure)
    return {"username": user.username, "csrf": csrf}


@router.post("/auth/logout")
def logout(
    request: Request,
    response: Response,
    p: Principal = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    close_session(db, request.cookies.get(SESSION_COOKIE, ""))
    audit.record(db, request.app.state.clock, p.user.username, "auth.logout")
    response.delete_cookie(SESSION_COOKIE)
    response.delete_cookie(CSRF_COOKIE)
    return {"ok": True}


@router.get("/auth/me")
def me(p: Principal = Depends(current_user)) -> dict[str, Any]:
    return {"username": p.user.username, "csrf": p.session.csrf_token}


# ---------- rules ----------
@router.get("/rules")
def rules(request: Request, _: Principal = Depends(current_user)) -> dict[str, Any]:
    h = request.app.state.rules
    return {
        "rules": h.rules.model_dump(mode="json"),
        "verify_paths": h.verify_paths,
        "verified_paths": h.verified_paths,
        "firm_version": h.firm_version,
        "standard_version": h.standard_version,
        "error": h.error,
    }


# ---------- connections (D3) ----------
def _vault(request: Request) -> Vault:
    try:
        return Vault(request.app.state.settings.master_key.get_secret_value())
    except MasterKeyMissing as e:
        raise HTTPException(503, str(e)) from e


async def _extras(request: Request) -> dict[str, dict[str, Any]]:
    st = request.app.state
    ta = st.ta
    ver = await ta.version() if ta.installed() else None
    latest = await conn.latest_ta_tag(st.http)
    return {
        "tradingagents": {
            "installed_version": ver.data.get("version") if ver and ver.ok else None,
            "install_error": None if (ver and ver.ok) else (ver.data.get("error") if ver else "not installed"),
            "pinned_version": ta.pinned_version,
            "pinned_commit": st.rules.rules.bias.pinned_commit,
            "latest_tag": latest,
            "llm_key_urls": {k: v["keys_url"] for k, v in LLM_PROVIDERS.items()},
        }
    }


@router.get("/connections")
async def list_connections(
    request: Request,
    _: Principal = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    st = request.app.state
    views = conn.list_views(db, st.clock, await _extras(request))
    required = [v for v in views if v["required"]]
    return {
        "connections": views,
        "indicators": conn.indicator_views(db, st.clock),
        "summary": {
            "connected": sum(v["status"] in ("connected", "saved") for v in views),
            "total": sum(v["status"] != "link" for v in views),
            "required_ready": all(v["status"] == "connected" for v in required),
        },
        "webhook_path": "/api/webhook/tradingview",
        "master_key_set": bool(st.settings.master_key.get_secret_value()),
    }


class SaveIn(BaseModel):
    values: dict[str, str]


async def _view_after(request: Request, db: Session, pid: str) -> dict[str, Any]:
    st = request.app.state
    views = conn.list_views(db, st.clock, await _extras(request))
    view = next(v for v in views if v["id"] == pid)
    await st.hub.broadcast("connection.updated", {"id": pid, "status": view["status"], "detail": view["detail"]})
    return view


@router.put("/connections/{pid}")
async def save_connection(
    pid: str,
    body: SaveIn,
    request: Request,
    p: Principal = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    st = request.app.state
    try:
        get_provider(pid)
    except KeyError as e:
        raise HTTPException(404, "unknown connection") from e
    try:
        await conn.save_and_test(db, _vault(request), st.clock, st.http, st.ta, pid, body.values, p.user.username)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    db.commit()
    return await _view_after(request, db, pid)


@router.post("/connections/{pid}/test")
async def test_connection(
    pid: str,
    request: Request,
    p: Principal = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    st = request.app.state
    try:
        await conn.retest(db, _vault(request), st.clock, st.http, st.ta, pid, p.user.username)
    except KeyError as e:
        raise HTTPException(404, "unknown connection") from e
    except LookupError as e:
        raise HTTPException(409, str(e)) from e
    db.commit()
    return await _view_after(request, db, pid)


@router.delete("/connections/{pid}")
async def delete_connection(
    pid: str,
    request: Request,
    p: Principal = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        conn.remove(db, request.app.state.clock, pid, p.user.username)
    except KeyError as e:
        raise HTTPException(404, "unknown connection") from e
    db.commit()
    return await _view_after(request, db, pid)


class IndicatorIn(BaseModel):
    source: str = Field(min_length=10)


@router.put("/indicators/{iid}")
async def save_indicator(
    iid: str,
    body: IndicatorIn,
    request: Request,
    p: Principal = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    st = request.app.state
    try:
        conn.save_indicator(db, st.clock, iid, body.source, p.user.username)
    except KeyError as e:
        raise HTTPException(404, "unknown indicator") from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    db.commit()
    await st.hub.broadcast("connection.updated", {"id": iid})
    return {"indicators": conn.indicator_views(db, st.clock)}


@router.get("/connections/tradingagents/models")
async def ta_models(request: Request, _: Principal = Depends(current_user)) -> dict[str, Any]:
    res = await request.app.state.ta.catalog()
    if not res.ok:
        raise HTTPException(503, f"TradingAgents not available: {res.data.get('error')}")
    return {"catalog": res.data.get("catalog", {})}


def http_client(timeout: float) -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=timeout, follow_redirects=False, headers={"User-Agent": "Paytience/0.1"})
