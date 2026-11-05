"""Shared request dependencies: DB session, auth, CSRF."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth import CSRF_HEADER, SESSION_COOKIE, csrf_ok, resolve_session
from app.models import AuthSession, User


def get_db(request: Request) -> Iterator[Session]:
    with request.app.state.sessionmaker() as s:
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise


@dataclass
class Principal:
    user: User
    session: AuthSession


def current_user(request: Request, db: Session = Depends(get_db)) -> Principal:
    res = resolve_session(db, request.cookies.get(SESSION_COOKIE), request.app.state.clock)
    if res is None:
        raise HTTPException(401, "login required")
    user, sess = res
    if request.method not in ("GET", "HEAD", "OPTIONS") and not csrf_ok(sess, request.headers.get(CSRF_HEADER)):
        raise HTTPException(403, "CSRF token missing or invalid")
    return Principal(user, sess)
