"""Small in-process event bus (§19): publish from anywhere (sync or async, any thread) → WebSocket broadcast.

Notifications are also stored in the `notifications` table. DB writes run in a worker thread so a caller that holds
an open SQLite write transaction on the event loop never deadlocks the loop. Failures are logged, never raised:
publishing must not break the trading path that called it.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from concurrent.futures import Future
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy.orm import Session, sessionmaker

from app.models import Notification

log = structlog.get_logger()

# §19 WS events (+ a few app-specific ones the UI already listens to).
EVENTS: frozenset[str] = frozenset(
    {
        "signal.updated",
        "approval.created",
        "approval.expired",
        "order.updated",
        "position.updated",
        "account.updated",
        "risk.alert",
        "risk.eval_mode.changed",
        "risk.day_lockin",
        "cooldown.changed",
        "payout.ready",
        "automation.changed",
        "job.progress",
        "system.status",
        "notification",
        # existing app-specific events
        "connection.updated",
        "risk.settings_changed",
        "payout.changed",
        "live.changed",
    }
)
LEVELS = ("info", "warn", "error")


class UnknownEvent(ValueError):
    pass


@dataclass
class Job:
    id: str
    kind: str
    label: str
    status: str  # running | done | failed
    progress: int
    at: str

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class EventBus:
    hub: Any
    sessionmaker: sessionmaker[Session]
    now: Callable[[], datetime]
    loop: asyncio.AbstractEventLoop | None = None
    jobs: dict[str, Job] = field(default_factory=dict)
    _pending: set[asyncio.Future[Any] | Future[Any]] = field(default_factory=set)

    # ---------- plumbing ----------
    def bind(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

    def _submit(self, coro_fn: Callable[[], Any]) -> None:
        """Run `coro_fn()` on the bound loop, from the loop itself or from any other thread."""
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is not None:
            t: asyncio.Future[Any] = running.create_task(coro_fn())
        elif self.loop is not None and self.loop.is_running():
            t = asyncio.run_coroutine_threadsafe(coro_fn(), self.loop)  # type: ignore[assignment]
        else:
            log.warning("events.no_loop")  # nothing to broadcast to (app not started)
            return
        self._pending.add(t)
        t.add_done_callback(self._pending.discard)

    async def drain(self) -> None:
        """Wait for everything published so far (tests, shutdown)."""
        while self._pending:
            await asyncio.gather(*(asyncio.wrap_future(f) for f in list(self._pending)), return_exceptions=True)

    async def emit(self, event: str, data: dict[str, Any]) -> None:
        if event not in EVENTS:
            raise UnknownEvent(event)
        try:
            await self.hub.broadcast(event, data)
        except Exception as e:  # never break the caller
            log.error("events.broadcast_failed", ws_event=event, error=type(e).__name__)

    def publish(self, event: str, data: dict[str, Any]) -> None:
        if event not in EVENTS:
            raise UnknownEvent(event)
        self._submit(lambda: self.emit(event, data))

    # ---------- notifications ----------
    def _store(self, level: str, title: str, body: str, kind: str) -> dict[str, Any] | None:
        try:
            with self.sessionmaker() as s:
                n = Notification(
                    level=level,
                    title=title[:160],
                    body=body,
                    kind=kind[:32],
                    channels=["in_app"],
                    created_at=self.now(),
                )
                s.add(n)
                s.commit()
                return notification_row(n)
        except Exception as e:  # never silent, never raised into the trading path
            log.error("events.notification_store_failed", error=type(e).__name__)
            return None

    async def _notify(self, level: str, title: str, body: str, kind: str) -> None:
        row = await asyncio.to_thread(self._store, level, title, body, kind)
        if row is not None:
            await self.emit("notification", row)

    def notify(self, level: str, title: str, body: str = "", kind: str = "general") -> None:
        if level not in LEVELS:
            level = "error"
        self._submit(lambda: self._notify(level, title, body, kind))

    # ---------- jobs ----------
    def job(self, jid: str, kind: str, label: str, status: str, progress: int = 0) -> None:
        j = Job(jid, kind, label, status, max(0, min(100, progress)), self.now().isoformat())
        if status == "running":
            self.jobs[jid] = j
        else:
            self.jobs.pop(jid, None)
        self.publish("job.progress", j.as_dict())


def notification_row(n: Notification) -> dict[str, Any]:
    return {
        "id": n.id,
        "level": n.level,
        "kind": n.kind,
        "title": n.title,
        "body": n.body,
        "created_at": n.created_at.isoformat(),
        "read": n.read_at is not None,
    }
