"""Dashboard login (§20): Argon2 hashes, opaque session cookie, CSRF double-submit, login rate limit."""

from __future__ import annotations

import hashlib
import secrets
import time
from collections import defaultdict, deque
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.clock import Clock
from app.models import AuthSession, User

_ph = PasswordHasher()
SESSION_COOKIE = "pt_session"
CSRF_COOKIE = "pt_csrf"
CSRF_HEADER = "x-csrf-token"


def hash_password(pw: str) -> str:
    if len(pw) < 12:
        raise ValueError("password must be at least 12 characters")
    return _ph.hash(pw)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_user(s: Session, username: str, password: str) -> User:
    if s.execute(select(User).where(User.username == username)).scalar_one_or_none():
        raise ValueError("user exists")
    u = User(username=username, password_hash=hash_password(password))
    s.add(u)
    s.flush()
    return u


def authenticate(s: Session, username: str, password: str) -> User | None:
    u = s.execute(select(User).where(User.username == username, User.is_active)).scalar_one_or_none()
    if u is None:
        _ph.hash("timing-equalizer-password")  # equalize timing for unknown users
        return None
    try:
        _ph.verify(u.password_hash, password)
    except (VerificationError, InvalidHashError):
        return None
    return u


def open_session(s: Session, user: User, clock: Clock, hours: int) -> tuple[str, str]:
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
    s.add(
        AuthSession(
            token_hash=_token_hash(token),
            user_id=user.id,
            csrf_token=csrf,
            expires_at=clock.now() + timedelta(hours=hours),
        )
    )
    s.flush()
    return token, csrf


def resolve_session(s: Session, token: str | None, clock: Clock) -> tuple[User, AuthSession] | None:
    if not token:
        return None
    row = s.execute(select(AuthSession).where(AuthSession.token_hash == _token_hash(token))).scalar_one_or_none()
    if row is None or row.expires_at <= clock.now():
        return None
    user = s.get(User, row.user_id)
    if user is None or not user.is_active:
        return None
    return user, row


def close_session(s: Session, token: str) -> None:
    s.execute(delete(AuthSession).where(AuthSession.token_hash == _token_hash(token)))


def csrf_ok(row: AuthSession, header_value: str | None) -> bool:
    return bool(header_value) and secrets.compare_digest(row.csrf_token, header_value or "")


class RateLimiter:
    """Sliding window of FAILED attempts per client (in-process; fine for a single-node local deploy).

    Successful logins never count, so normal use can't lock the owner out.
    """

    def __init__(self, max_failures: int, per_seconds: float) -> None:
        self.max_failures, self.per = max_failures, per_seconds
        self._fails: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str, t: float) -> deque[float]:
        q = self._fails[key]
        while q and q[0] <= t - self.per:
            q.popleft()
        return q

    def blocked(self, key: str, now: float | None = None) -> bool:
        t = time.monotonic() if now is None else now
        return len(self._prune(key, t)) >= self.max_failures

    def fail(self, key: str, now: float | None = None) -> None:
        t = time.monotonic() if now is None else now
        self._prune(key, t).append(t)
