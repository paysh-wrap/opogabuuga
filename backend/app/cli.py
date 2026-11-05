"""Admin CLI: `python -m app.cli keys | create-admin [user] | set-password [user] | rename-user OLD NEW`."""

from __future__ import annotations

import getpass
import os
import secrets
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import Engine

from app import audit
from app.auth import create_user, hash_password
from app.clock import SystemClock
from app.crypto import new_master_key
from app.db import Base, make_engine, make_sessionmaker
from app.models import User
from app.settings import get_settings

DEFAULT_ADMIN = "PayDay"


@contextmanager
def _engine() -> Iterator[Engine]:
    """Engine that is always disposed AFTER every session using it has closed."""
    url = get_settings().database_url
    if url.startswith("sqlite:///"):
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    engine = make_engine(url)
    try:
        Base.metadata.create_all(engine)
        yield engine
    finally:
        engine.dispose()


def _password() -> str:
    pw = os.environ.pop("PAYTIENCE_ADMIN_PASSWORD", "") or getpass.getpass("Dashboard password: ")
    if not os.environ.get("CI") and pw and sys.stdin.isatty() and getpass.getpass("Repeat password: ") != pw:
        raise SystemExit("passwords do not match")
    return pw


def _admin(cmd: str, username: str) -> int:
    pw = _password()
    with _engine() as engine, make_sessionmaker(engine)() as s:
        existing = s.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if cmd == "create-admin":
            if existing:
                print(f"user {username!r} already exists (use set-password)")
                return 1
            create_user(s, username, pw)
        else:
            if not existing:
                print(f"no user {username!r}")
                return 1
            existing.password_hash = hash_password(pw)
        audit.record(s, SystemClock(), "cli", f"auth.{cmd}", username, {})
        s.commit()
    print(f"{cmd}: ok for user {username!r}")
    return 0


def _rename(old: str, new: str) -> int:
    with _engine() as engine, make_sessionmaker(engine)() as s:
        u = s.execute(select(User).where(User.username == old)).scalar_one_or_none()
        if u is None:
            print(f"no user {old!r}")
            return 1
        if s.execute(select(User).where(User.username == new)).scalar_one_or_none():
            print(f"user {new!r} already exists")
            return 1
        u.username = new
        audit.record(s, SystemClock(), "cli", "auth.rename-user", new, {"from": old})
        s.commit()
    print(f"renamed {old!r} → {new!r}")
    return 0


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else ""
    if cmd == "keys":
        print(f"PAYTIENCE_MASTER_KEY={new_master_key()}")
        print(f"PAYTIENCE_WEBHOOK_SECRET={secrets.token_urlsafe(32)}")
        return 0
    if cmd in ("create-admin", "set-password"):
        username = (argv[1] if len(argv) > 1 else "") or get_settings().admin_user or DEFAULT_ADMIN
        return _admin(cmd, username)
    if cmd == "rename-user" and len(argv) == 3:
        return _rename(argv[1], argv[2])
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
