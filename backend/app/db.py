"""SQLAlchemy 2 engine/session. SQLite now, Postgres-ready (Decimal stored exactly on both)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Dialect, Numeric, String, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator


class DecimalType(TypeDecorator[Decimal]):
    """Exact Decimal: TEXT on SQLite (which has no decimal type), NUMERIC(24,8) elsewhere."""

    impl = String(48)
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> Any:
        if dialect.name == "sqlite":
            return dialect.type_descriptor(String(48))
        return dialect.type_descriptor(Numeric(24, 8, asdecimal=True))

    def process_bind_param(self, value: Decimal | None, dialect: Dialect) -> Any:
        if value is None:
            return None
        if not isinstance(value, Decimal):
            raise TypeError(f"DecimalType needs Decimal, got {type(value).__name__}")  # no floats, ever
        return str(value) if dialect.name == "sqlite" else value

    def process_result_value(self, value: Any, dialect: Dialect) -> Decimal | None:
        return None if value is None else Decimal(str(value))


class UTCDateTime(TypeDecorator[datetime]):
    """Always timezone-aware UTC in Python; naive UTC in SQLite."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> Any:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime not allowed")
        return value.astimezone(UTC)

    def process_result_value(self, value: Any, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        dt: datetime = value
        return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


class Base(DeclarativeBase):
    pass


def make_engine(url: str) -> Engine:
    kwargs: dict[str, Any] = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(url, **kwargs)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _pragmas(dbapi_conn: Any, _rec: Any) -> None:
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA journal_mode=WAL")
            cur.close()

    return engine


def make_sessionmaker(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)


def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    with factory() as s:
        yield s
