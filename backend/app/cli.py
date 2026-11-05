"""Admin CLI: `python -m app.cli keys | create-admin [user] | set-password [user] | rename-user OLD NEW`."""

from __future__ import annotations

import getpass
import os
import secrets
import sys

from app.auth import create_user, hash_password
from app.clock import SystemClock
from app.crypto import new_master_key
from app.db import Base, make_engine, make_sessionmaker
from app.settings import get_settings

DEFAULT_ADMIN = "PayDay"


def _password() -> str:
    pw = os.environ.pop("PAYTIENCE_ADMIN_PASSWORD", "") or getpass.getpass("Dashboard password: ")
    if not os.environ.get("CI") and pw and sys.stdin.isatty() and getpass.getpass("Repeat password: ") != pw:
        raise SystemExit("passwords do not match")
    return pw


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else ""
    if cmd == "keys":
        print(f"PAYTIENCE_MASTER_KEY={new_master_key()}")
        print(f"PAYTIENCE_WEBHOOK_SECRET={secrets.token_urlsafe(32)}")
        return 0
    if cmd in ("create-admin", "set-password"):
        from sqlalchemy import select

        from app import audit
        from app.models import User

        st = get_settings()
        if st.database_url.startswith("sqlite:///"):
            from pathlib import Path

            Path(st.database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        engine = make_engine(st.database_url)
        Base.metadata.create_all(engine)
        username = (argv[1] if len(argv) > 1 else "") or st.admin_user or DEFAULT_ADMIN
        pw = _password()
        with make_sessionmaker(engine)() as s:
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
    if cmd == "rename-user" and len(argv) == 3:
        from sqlalchemy import select

        from app import audit
        from app.models import User

        st = get_settings()
        engine = make_engine(st.database_url)
        with make_sessionmaker(engine)() as s:
            u = s.execute(select(User).where(User.username == argv[1])).scalar_one_or_none()
            if u is None:
                print(f"no user {argv[1]!r}")
                return 1
            if s.execute(select(User).where(User.username == argv[2])).scalar_one_or_none():
                print(f"user {argv[2]!r} already exists")
                return 1
            u.username = argv[2]
            audit.record(s, SystemClock(), "cli", "auth.rename-user", argv[2], {"from": argv[1]})
            s.commit()
        print(f"renamed {argv[1]!r} → {argv[2]!r}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
