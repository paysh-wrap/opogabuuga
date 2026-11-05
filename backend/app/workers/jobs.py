"""arq worker. Phase 1: health job only; scheduled jobs arrive in Phases 7–9 (§15, §16, §17)."""

from __future__ import annotations

from typing import Any, ClassVar

from arq.connections import RedisSettings

from app.settings import get_settings


async def ping(ctx: dict[str, Any]) -> str:
    return "pong"


class WorkerSettings:
    functions: ClassVar[list[Any]] = [ping]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
