"""D160: TradingAgents bias runs before each session for the AR Model beside NOISE (pure helpers + audit rows).

`strategy.advisor.pre_session_runs_min` (plan file, default 240 / 60 / 30) = minutes before the session start (the
earliest Order Flow entry window, ET). Each run reuses the existing bias job (bias/service.run_bias, TradingAgents
subprocess, ledger rows) and stores one audit row per market and run (`order_flow.ar_bias_run`, code AR_BIAS_RUN):
rating + probabilities, or NO_CALL (AI key not connected / run failed). Advisory only: this module never blocks a
trade; blocking stays with the D151 advisor GATE on a proven ledger (tighten-only)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.bias import ledger as L
from app.bias.of_advisor import SIDE, _latest_bias, session_start_min
from app.bias.policy import Policy, combine
from app.models import AuditLog

CODE = "AR_BIAS_RUN"
ACTION = "order_flow.ar_bias_run"
SOURCE = "ESTIMATED delta (online data)"
EVIDENCE = (
    "No edge shown on estimated data: UNVERIFIED, paper first. Evidence: docs/results/new_strategies and "
    "docs/results/session22."
)


def enabled(rules: Any) -> bool:
    st = rules.strategy
    return bool(st.order_flow and st.order_flow_cfg.ar_side_by_side and st.advisor.mode != "OFF")


def run_times(rules: Any) -> list[tuple[int, str]]:
    """[(minutes before, ET HH:MM)] for every configured run, earliest first. Times never go before 00:00."""
    start = session_start_min(rules)
    out = []
    for m in sorted(rules.strategy.advisor.pre_session_runs_min, reverse=True):
        t = max(0, start - m)
        out.append((m, f"{t // 60:02d}:{t % 60:02d}"))
    return out


def due(now: datetime, rules: Any, minutes: int, last: str | None, sess: date) -> bool:
    """True once the run time passed, before the session start, once per session and run; only the latest due run."""
    from app.bias.service import due as _due
    from app.clock import to_et

    times = dict(run_times(rules))
    at = times.get(minutes)
    if not enabled(rules) or at is None:
        return False
    local = to_et(now)
    cur = local.hour * 60 + local.minute

    def mins(t: str) -> int:
        return int(t[:2]) * 60 + int(t[3:])

    if any(mins(t) > mins(at) and mins(t) <= cur for t in times.values()):
        return False  # a later run is already due: no stale catch-up of an earlier one
    return _due(now, at, last, sess) and cur < session_start_min(rules)


def entity(symbol: str, day: date, minutes: int) -> str:
    return f"{symbol}-AR-BIAS-{day.isoformat()}-{minutes}"


def record_run(s: Session, rules: Any, clock: Any, sess: date, minutes: int, failed: str | None = None) -> None:
    """One audit row per Order Flow market for this run, from the latest bias row (NO_CALL when none is usable)."""
    for sym in rules.strategy.order_flow_cfg.instruments:
        proxy = rules.instrument(sym).bias_proxy
        row = _latest_bias(s, sess, proxy)
        side = SIDE.get(row.mapped) if row is not None and failed is None else None
        p: float | None = None
        if side is not None and row is not None:
            ta, vd, vc = L.parse_label(row.raw_rating)
            p = combine(ta, vd, vc, Policy(bias_matters=True)).prob_up
        reason = None
        if side is None:
            reason = failed or (
                "AI key not connected" if row is not None and row.raw_rating == "NOT_CONFIGURED" else "no usable rating"
            )
        audit.record(
            s,
            clock,
            "bias",
            ACTION,
            entity(sym, sess, minutes),
            {
                "code": CODE,
                "minutes_before": minutes,
                "symbol": sym,
                "proxy": proxy,
                "status": "OK" if side is not None else "NO_CALL",
                "side": side,
                "rating": None if row is None or side is None else row.raw_rating,
                "prob_up": None if p is None else round(p, 4),
                "prob_down": None if p is None else round(1 - p, 4),
                "reason": reason,
                "at": clock.now().isoformat(),
            },
        )
    s.commit()


def view(s: Session, rules: Any, day: date) -> list[dict[str, Any]]:
    """The Order Flow card: every configured run with its time and the latest stored result per market."""
    syms = list(rules.strategy.order_flow_cfg.instruments)
    out = []
    for m, at in run_times(rules):
        results = []
        for sym in syms:
            row = s.execute(
                select(AuditLog)
                .where(AuditLog.action == ACTION, AuditLog.entity == entity(sym, day, m))
                .order_by(AuditLog.id.desc())
                .limit(1)
            ).scalar_one_or_none()
            results.append(dict(row.payload or {}) if row is not None else {"symbol": sym, "status": "PENDING"})
        out.append({"minutes_before": m, "at": at, "results": results})
    return out
