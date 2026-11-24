"""D109: TradingAgents as an ADVISOR for the Order Flow strategy (Order Flow page toggle, default OFF).

Reuses the daily bias job (bias/service.run_bias → ta_runner.py subprocess JSON; TradingAgents is never imported in
the API process) for the Order Flow instruments' proxies, once per session at `ta_advisor_lead_min` before the
earliest Order Flow entry window start (ET, injected Clock). Each market's advice is stored as an audit row
(`order_flow.ta_advice`, code OF_TA_ADVICE). Failure / no key / unknown rating = NO advice: trading is never blocked.

Advisory only: an opposite-side ORDER_FLOW signal is annotated and warned; it is skipped (OF_TA_DISAGREES) only when
the plan flag `ta_advisor_blocks` is true AND the AI-accuracy ledger has proven the call (bias/ledger.py)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.bias import ledger as L
from app.bias.policy import Policy, combine
from app.models import AuditLog, BiasDecision

CODE = "OF_TA_ADVICE"
SKIP = "OF_TA_DISAGREES"
ACTION = "order_flow.ta_advice"
SIDE = {"LONG_ONLY": "LONG", "SHORT_ONLY": "SHORT", "NEUTRAL": "NEUTRAL"}


def session_start_min(rules: Any) -> int:
    """ET minute of day of the earliest entry window start of the Order Flow markets (the session start)."""
    starts = []
    for sym in rules.strategy.order_flow_cfg.instruments:
        inst = rules.instrument(sym)
        for a, _b in inst.windows or rules.internal.windows:
            h, m = (int(x) for x in a.split(":"))
            starts.append(h * 60 + m)
    return min(starts)


def advisor_at(rules: Any) -> str:
    """ET time the advisor runs: lead minutes before the earliest entry window start of the Order Flow markets."""
    t = max(0, session_start_min(rules) - rules.strategy.order_flow_cfg.ta_advisor_lead_min)
    return f"{t // 60:02d}:{t % 60:02d}"


def enabled(rules: Any) -> bool:
    return bool(rules.strategy.order_flow and rules.strategy.order_flow_cfg.ta_advisor)


def proxies(rules: Any) -> list[str]:
    return sorted({rules.instrument(s).bias_proxy for s in rules.strategy.order_flow_cfg.instruments})


def entity(symbol: str, day: date) -> str:
    return f"{symbol}-OF-TA-{day.isoformat()}"


def _latest_bias(s: Session, sess: date, proxy: str) -> BiasDecision | None:
    return s.execute(
        select(BiasDecision)
        .where(BiasDecision.session_date == sess, BiasDecision.proxy == proxy)
        .order_by(BiasDecision.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def record(s: Session, rules: Any, clock: Any, sess: date) -> dict[str, dict[str, Any]]:
    """Store today's advice per Order Flow market from the bias rows (OF_TA_ADVICE). No usable row = no advice."""
    out: dict[str, dict[str, Any]] = {}
    for sym in rules.strategy.order_flow_cfg.instruments:
        row = _latest_bias(s, sess, rules.instrument(sym).bias_proxy)
        side = SIDE.get(row.mapped) if row is not None else None
        conf = None
        if row is not None and side is not None:
            ta, vd, vc = L.parse_label(row.raw_rating)
            p = combine(ta, vd, vc, Policy(bias_matters=True)).prob_up
            conf = round(max(p, 1 - p) * 100)
        adv = {
            "code": CODE,
            "symbol": sym,
            "proxy": rules.instrument(sym).bias_proxy,
            "side": side,  # None = no advice (failure / no key / unknown rating) — never blocks trading
            "raw": None if row is None else row.raw_rating,
            "confidence": conf,
            "at": clock.now().isoformat(),
        }
        audit.record(s, clock, "bias", ACTION, entity(sym, sess), adv)
        out[sym] = adv
    s.commit()
    return out


def advice(s: Session, symbol: str, day: date) -> dict[str, Any] | None:
    row = s.execute(
        select(AuditLog)
        .where(AuditLog.action == ACTION, AuditLog.entity == entity(symbol, day))
        .order_by(AuditLog.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    return None if row is None else dict(row.payload or {})


def verdict(s: Session, rules: Any, symbol: str, day: date, direction: str) -> tuple[dict[str, Any] | None, str | None]:
    """(annotation for the signal or None, skip code). D176: the skip code is ALWAYS None - advice only."""
    cfg = rules.strategy.order_flow_cfg
    if not cfg.ta_advisor:
        return None, None
    adv = advice(s, symbol, day)
    if adv is None or adv.get("side") not in ("LONG", "SHORT", "NEUTRAL"):
        return {"side": None, "agrees": None, "advisory": True}, None
    agrees = adv["side"] in ("NEUTRAL", direction)
    note = {"side": adv["side"], "confidence": adv.get("confidence"), "agrees": agrees, "advisory": True}
    return note, None  # D176: advice only - `ta_advisor_blocks` (old saves) is ignored, never a skip


def due(now: datetime, rules: Any, last: str | None, sess: date) -> bool:
    from app.bias.service import due as _due

    return enabled(rules) and _due(now, advisor_at(rules), last, sess)
