"""D78 fast-track backfill: run the daily AI bias (TradingAgents + Vibe-Trading) for the last N MNQ sessions with an
as-of date, so the user sees an ESTIMATE of accuracy before the live record (D55, 30+ calls ≥ 70%) has built up.

Hard separation from the live proof: backfill rows are stored under proxy `<proxy>.BF` (e.g. "QQQ.BF") with version
`BACKFILL:<ver>`. Every live reader (today_bias, ledger, may_block, sizing_call, the live ledger/proof) filters on the
plain proxy, so a backfill row can NEVER count toward "AI may block". Backfill accuracy is shown separately as
"estimate (possible hindsight)": the LLMs' own training data/news tools may know how those days ended.

TradingAgents runs only through the existing `.venv-ta` subprocess runner, Vibe-Trading through `.venv-vt`; nothing is
imported into the API process. One call at a time, a pause between calls, and the run STOPS on repeated errors
(banner + notification), never silently. Resumable: days already stored are skipped.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.bias import vibe_trading as vt
from app.bias.service import MARKET_OF, OK
from app.bias.tradingagents_adapter import TradingAgentsAdapter, map_rating
from app.models import ApiCredential, BiasDecision

SUFFIX = ".BF"
MAX_DAYS = 250
MAX_CONSECUTIVE_ERRORS = 3
PAUSE_S = 5.0  # rate limit between calls
# Rough planning guesses only (a TradingAgents run is a multi-agent debate; Qwen is cheap). Shown as "about".
EST_USD = {"ta": 0.25, "vt": 0.10}


def bf_proxy(proxy: str) -> str:
    return proxy + SUFFIX


def is_backfill(proxy: str) -> bool:
    return proxy.endswith(SUFFIX)


def last_sessions(today: date, n: int) -> list[date]:
    """The last n weekdays before `today`, oldest first (market holidays simply end up unscored)."""
    out: list[date] = []
    d = today
    while len(out) < n:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            out.append(d)
    return sorted(out)


def pending_days(s: Session, proxy: str, days: list[date]) -> list[date]:
    done = {
        r.session_date
        for r in s.execute(
            select(BiasDecision).where(BiasDecision.proxy == bf_proxy(proxy), BiasDecision.session_date.in_(days))
        ).scalars()
        if r.mapped in OK
    }
    return [d for d in days if d not in done]


def estimate(n_days: int, with_vt: bool, provider: str) -> dict[str, Any]:
    calls = n_days * (2 if with_vt else 1)
    usd = n_days * (EST_USD["ta"] + (EST_USD["vt"] if with_vt else 0))
    return {
        "days": n_days,
        "tool_runs": calls,
        "provider": provider,
        "est_usd": round(usd, 2),
        "est_minutes": round(n_days * (2 if with_vt else 1.2), 0),
        "note": "rough guess — check your provider's usage page; each run is many model calls",
    }


@dataclass
class Job:
    status: str = "idle"  # idle | running | done | cancelled | stopped_on_error
    total: int = 0
    done: int = 0
    failed: int = 0
    skipped: int = 0
    current: str | None = None
    provider: str = ""
    days_requested: int = 0
    error: str | None = None
    started: str | None = None
    finished: str | None = None
    cancel: bool = field(default=False, repr=False)
    task: Any = field(default=None, repr=False)

    def view(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if k not in ("cancel", "task")}


def _provider(s: Session, vault: Any) -> tuple[ApiCredential | None, ApiCredential | None, str]:
    cred = s.execute(select(ApiCredential).where(ApiCredential.provider == "tradingagents")).scalar_one_or_none()
    vcred = s.execute(select(ApiCredential).where(ApiCredential.provider == "vibetrading")).scalar_one_or_none()
    prov = ""
    if cred is not None:
        try:
            prov = str(vault.open(cred.ciphertext).get("llm_provider", ""))
        except (ValueError, KeyError):
            prov = "?"
    return cred, vcred, prov


def preview(s: Session, vault: Any, rules: Any, today: date, n: int, vt_root: Any) -> dict[str, Any]:
    proxy = rules.instruments["MNQ"].bias_proxy
    cred, vcred, prov = _provider(s, vault)
    todo = pending_days(s, proxy, last_sessions(today, n))
    with_vt = vcred is not None and vt_root is not None
    return {
        **estimate(len(todo), with_vt, prov or "not configured"),
        "configured": cred is not None,
        "with_vt": with_vt,
    }


async def run_job(
    job: Job,
    sessionmaker: Callable[[], Session],
    ta: TradingAgentsAdapter,
    vault: Any,
    rules: Any,
    clock: Any,
    notify: Callable[..., Any],
    today: date,
    n: int,
    vt_root: Any,
    pause_s: float = PAUSE_S,
) -> None:
    """Background task. Never raises; every failure ends in status + banner."""
    proxy = rules.instruments["MNQ"].bias_proxy
    market = MARKET_OF.get(proxy, "MNQ")
    consecutive = 0
    try:
        with sessionmaker() as s:
            cred, vcred, job.provider = _provider(s, vault)
            if cred is None:
                raise ValueError("TradingAgents LLM key not set (Connections page)")
            env = TradingAgentsAdapter.env_for(vault.open(cred.ciphertext), None)
            venv = vt.env_for(vault.open(vcred.ciphertext)) if vcred is not None and vt_root is not None else None
            todo = pending_days(s, proxy, last_sessions(today, n))
            job.skipped = n - len(todo)
            job.total = len(todo)
            for day in todo:
                if job.cancel:
                    job.status = "cancelled"
                    break
                job.current = day.isoformat()
                res = await ta.run(proxy, day, env)
                raw = str(res.data.get("rating") or "") if res.ok else "ERROR"
                mapped, alert = map_rating(raw, rules.bias.rating_map)
                if alert:  # no valid TradingAgents rating: store nothing, count the error, maybe stop
                    job.failed += 1
                    consecutive += 1
                    job.error = f"{day}: {str(res.data.get('error') or raw)[:200]}"
                    if consecutive >= MAX_CONSECUTIVE_ERRORS:
                        job.status = "stopped_on_error"
                        notify(
                            "error", "AI backfill stopped", f"{MAX_CONSECUTIVE_ERRORS} errors in a row — {job.error}"
                        )
                        break
                    await asyncio.sleep(pause_s)
                    continue
                consecutive = 0
                label, reasoning = raw, str(res.data.get("decision") or "")[:20000]
                if venv is not None and vt_root is not None:
                    outlook, vstatus = await vt.run(
                        vt.executable(Path(vt_root)),
                        venv,
                        vt.prompt(proxy, market, day.isoformat(), None, backfill=True),
                        Path(vt_root) / "data" / "vibe-trading",
                    )
                    if outlook is not None:
                        label = f"{raw}·VT {outlook.direction} {outlook.confidence}"
                        reasoning += f"\n\n[Blend] VT: {outlook.reason}"
                    else:
                        reasoning += f"\n\n[Blend] Vibe-Trading: {vstatus}"
                s.add(
                    BiasDecision(
                        session_date=day,
                        proxy=bf_proxy(proxy),
                        raw_rating=label[:32],
                        mapped=mapped,
                        reasoning=reasoning[:20000],
                        version=("BACKFILL:" + str(res.data.get("version") or ""))[:32],
                    )
                )
                s.commit()
                job.done += 1
                await asyncio.sleep(pause_s)
            if job.status == "running":
                job.status = "done"
            audit.record(s, clock, "bias", "bias.backfill", proxy, {"status": job.status, "done": job.done})
            s.commit()
    except Exception as e:  # never silent (§1.8)
        job.status = "stopped_on_error"
        job.error = f"{type(e).__name__}: {str(e)[:200]}"
        notify("error", "AI backfill stopped", job.error)
    finally:
        job.current = None
        job.finished = datetime.now().isoformat(timespec="seconds")
