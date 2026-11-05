"""Daily bias (§15): run TauricResearch/TradingAgents once per session on each enabled instrument's proxy ETF.

- Scheduled at `schedule.bias` (02:40 ET, D34), Mon–Fri. Latest row per (session, proxy) wins (today_bias).
- Failure / timeout / unknown rating → stored as NO_TRADE + alert (that instrument does not trade today).
- A failed proxy may be retried ("Run now"); a successful one is not re-run the same session.
- Live-only: always the CURRENT session date (never re-run history).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.bias.tradingagents_adapter import TradingAgentsAdapter, map_rating
from app.models import ApiCredential, BiasDecision

OK = ("LONG_ONLY", "SHORT_ONLY", "NEUTRAL")


def proxies(rules: Any) -> list[str]:
    return sorted({i.bias_proxy for i in rules.instruments.values() if i.enabled})


def _done(s: Session, sess: date, proxy: str) -> bool:
    row = s.execute(
        select(BiasDecision)
        .where(BiasDecision.session_date == sess, BiasDecision.proxy == proxy)
        .order_by(BiasDecision.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    return row is not None and row.mapped in OK


async def run_bias(
    s: Session, ta: TradingAgentsAdapter, vault: Any, rules: Any, clock: Any, sess: date, notify: Any
) -> dict[str, str]:
    cred = s.execute(select(ApiCredential).where(ApiCredential.provider == "tradingagents")).scalar_one_or_none()
    out: dict[str, str] = {}
    for proxy in proxies(rules):
        if _done(s, sess, proxy):
            continue
        raw, reasoning, version = "NOT_CONFIGURED", "TradingAgents LLM key not set (Connections page)", ""
        if cred is not None:
            try:
                env = TradingAgentsAdapter.env_for(vault.open(cred.ciphertext), None)
                res = await ta.run(proxy, sess, env)
            except (ValueError, KeyError) as e:
                raw, reasoning = "ERROR", f"credentials: {type(e).__name__}"
            else:
                d = res.data
                raw = str(d.get("rating") or "") if res.ok else "ERROR"
                reasoning = str(d.get("decision") or d.get("error") or "")[:20000]
                version = str(d.get("version") or "")
        mapped, alert = map_rating(raw, rules.bias.rating_map)
        s.add(
            BiasDecision(
                session_date=sess, proxy=proxy, raw_rating=raw[:32], mapped=mapped, reasoning=reasoning, version=version
            )
        )
        audit.record(s, clock, "bias", "bias.decided", proxy, {"raw": raw[:32], "mapped": mapped})
        if alert:
            notify("error", f"Bias {proxy}: NO TRADE today", f"{raw}: {reasoning[:200]}")
        out[proxy] = mapped
    s.commit()
    return out


def due(now: datetime, at: str, last: str | None, sess: date) -> bool:
    from app.clock import to_et

    local = to_et(now)
    h, m = (int(x) for x in at.split(":"))
    return local.weekday() < 5 and (local.hour, local.minute) >= (h, m) and last != sess.isoformat()
