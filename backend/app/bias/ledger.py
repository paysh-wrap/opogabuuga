"""D55 calibration ledger: every daily AI call (TradingAgents + Vibe-Trading) scored against the real session.

No new table: a call is the stored BiasDecision (raw_rating "BUY" or "BUY·VT SHORT 85"); the outcome is the market's
own RTH move from the 1-minute TradingView bars the app already stores (09:30 open → 16:00 close). Pure scoring lives
in app/bias/policy.py. The AI may BLOCK a side only once its record is proven (≥ min_calls scored calls, Wilson lower
bound ≥ the strategy's required accuracy, Brier < 0.25) AND both tools agree strongly today; until then it is ADVISORY.
Required accuracy: 70% for NOISE (89% of its trades already go with the day; break-even ≈ 70% — session 9 research)."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bias.policy import Call, LedgerStats, Policy, combine, ledger_stats, score, wilson_lower
from app.clock import ET
from app.models import Bar, BiasDecision

LABEL = re.compile(r"^\s*([A-Z_]+)(?:·VT\s+(LONG|SHORT|NEUTRAL)\s+(\d+))?")
NOISE_MIN_ACC = 0.70


def parse_label(label: str) -> tuple[str, str | None, int | None]:
    m = LABEL.match(label or "")
    if not m:
        return "", None, None
    return m.group(1), m.group(2), int(m.group(3)) if m.group(3) else None


def session_outcome(s: Session, symbol: str, day: date) -> bool | None:
    """True = the RTH session closed above its 09:30 open; None = bars missing (not scored)."""
    # D78: tolerate a few missing 1-minute bars at the edges (first bar within 09:31-09:35, last within 15:56-16:00)
    def at(h: int, m: int) -> datetime:
        return datetime(day.year, day.month, day.day, h, m, tzinfo=ET)

    base = select(Bar).where(Bar.symbol == symbol, Bar.tf == "1")
    first = s.execute(
        base.where(Bar.close_time >= at(9, 31), Bar.close_time <= at(9, 35)).order_by(Bar.close_time).limit(1)
    ).scalar_one_or_none()
    last = s.execute(
        base.where(Bar.close_time >= at(15, 56), Bar.close_time <= at(16, 0)).order_by(Bar.close_time.desc()).limit(1)
    ).scalar_one_or_none()
    if first is None or last is None or last.c == first.o:
        return None
    return last.c > first.o


def _calls(s: Session, proxy: str, since: date, until: date) -> list[BiasDecision]:
    rows = s.execute(
        select(BiasDecision)
        .where(BiasDecision.proxy == proxy, BiasDecision.session_date >= since, BiasDecision.session_date <= until)
        .order_by(BiasDecision.session_date, BiasDecision.id)
    ).scalars()
    last: dict[date, BiasDecision] = {}
    for r in rows:
        last[r.session_date] = r  # the latest decision of each session counts
    return [last[d] for d in sorted(last)]


def ledger(
    s: Session, proxy: str, symbol: str, today: date, pol: Policy, days: int = 120, through: date | None = None
) -> dict[str, Any]:
    """`through` = last session to score (default: yesterday; D78: today once the 16:00 bar is stored)."""
    rows, scored = [], []
    for d in _calls(s, proxy, today - timedelta(days=days), through or today - timedelta(days=1)):
        ta, vd, vc = parse_label(d.raw_rating)
        call = combine(ta, vd, vc, pol)
        up = session_outcome(s, symbol, d.session_date)
        hit = brier = None
        if up is not None:
            hit, brier = score(call.prob_up, call.direction, up)
            scored.append((hit, brier))
        rows.append(
            {
                "day": d.session_date.isoformat(),
                "label": d.raw_rating,
                "call": call.direction,
                "prob_up": call.prob_up,
                "strong": call.agree_strong,
                "up": up,
                "hit": hit,
                "brier": brier,
            }
        )
    st = ledger_stats(scored)
    return {"proxy": proxy, "symbol": symbol, "stats": st.__dict__, "rows": rows[-30:]}


def proven(st: LedgerStats, pol: Policy, min_acc: float) -> bool:
    return st.n >= pol.min_calls and st.wilson_lb >= min_acc and st.brier < 0.25


def may_block(s: Session, proxy: str, symbol: str, today: date, direction: int, min_acc: float) -> str | None:
    """Reason string when today's proven, strongly-agreed AI call is AGAINST `direction` (+1/−1); else None."""
    pol = Policy(bias_matters=True)
    calls = _calls(s, proxy, today, today)
    if not calls:
        return None
    ta, vd, vc = parse_label(calls[-1].raw_rating)
    call: Call = combine(ta, vd, vc, pol)
    if not call.agree_strong or call.direction in (0, direction):
        return None
    led = ledger(s, proxy, symbol, today, pol)
    st = LedgerStats(**led["stats"])
    return "BIAS_PROVEN_AGAINST" if proven(st, pol, min_acc) else None


def sizing_call(s: Session, proxy: str, symbol: str, today: date, min_acc: float, min_calls: int) -> int:
    """D74: today's AI call direction (+1/−1) for SIZING, only when the live record is proven
    (≥ min_calls scored calls, observed hit rate ≥ min_acc, Brier < 0.25); else 0 (no effect)."""
    pol = Policy(bias_matters=True)
    calls = _calls(s, proxy, today, today)
    if not calls:
        return 0
    ta, vd, vc = parse_label(calls[-1].raw_rating)
    call = combine(ta, vd, vc, pol)
    st = LedgerStats(**ledger(s, proxy, symbol, today, pol)["stats"])
    if st.n < min_calls or st.hit_rate < min_acc or st.brier >= 0.25:
        return 0
    return call.direction


def calls_needed(st: LedgerStats, min_calls: int, min_acc: float) -> dict[str, int | None]:
    """D78: how many MORE scored calls until the proof, (a) if future calls keep today's hit rate, (b) best case (all
    hits). None = cannot get there that way. Window = the newest 60 scored calls (ledger_stats)."""
    out: dict[str, int | None] = {"at_current_rate": None, "best_case": None}
    for key, rate in (("at_current_rate", st.hit_rate), ("best_case", 1.0)):
        hits = st.hit_rate * st.n
        for k in range(0, 301):
            n = st.n + k
            if n >= min_calls and n > 0 and wilson_lower(hits + rate * k, n) >= min_acc:
                out[key] = k
                break
    return out


def status(
    s: Session, proxy: str, symbol: str, today: date, min_acc: float, through: date | None = None
) -> dict[str, Any]:
    pol = Policy(bias_matters=True)
    led = ledger(s, proxy, symbol, today, pol, through=through)
    st = LedgerStats(**led["stats"])
    ok = proven(st, pol, min_acc)
    led["required_accuracy"] = min_acc
    led["min_calls"] = pol.min_calls
    led["calls_needed"] = calls_needed(st, pol.min_calls, min_acc)
    led["state"] = "PROVEN" if ok else ("WARMUP" if st.n < pol.min_calls else "UNPROVEN")
    led["badge"] = "MAY BLOCK (proven)" if ok else "ADVISORY"
    return led
