"""Three-way parity (§5.2): Python reference ↔ Paytience_Bridge alerts ↔ originals.

`replay_payloads` runs the Python indicators over recorded bars and produces exactly the webhook payloads the bridge
should have sent. `compare` diffs two payload streams. Mismatch blocks LIVE and Lab promotions.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.clock import session_date
from app.indicators.bars import Bar, HtfAggregator
from app.indicators.bigbeluga_mso import MsoEngine
from app.indicators.lunqfx_fractal import FractalEngine, FractalFields

PRICE_KEYS = ("c1_high", "c1_low", "t1", "t2", "invalid", "sweep_extreme", "cisd_level", "htf_atr14")
EXACT_KEYS = ("c1_time_ms", "sweep_time_ms", "cisd_before_c2_close", "t1_preticked", "c3_close_time_ms")
OSC_TOL = Decimal("0.5")
ATR_TOL = Decimal("0.01")


def _fractal_dict(f: FractalFields) -> dict[str, Any]:
    return {k: (str(v) if isinstance(v, Decimal) else v) for k, v in f.__dict__.items()}


def replay_payloads(
    bars: Iterable[Bar],
    *,
    symbol: str,
    profile: str,
    tf: str,
    htf_min: int,
    tick: Decimal,
    atr_period: int,
    pivot_left: int,
    pivot_right: int,
    osc_length: int,
) -> list[dict[str, Any]]:
    fe = FractalEngine(htf_min, tick, atr_period)
    mso = MsoEngine(pivot_left, pivot_right, osc_length)
    htf_mso = MsoEngine(pivot_left, pivot_right, osc_length)
    htf_agg = HtfAggregator(htf_min)
    out: list[dict[str, Any]] = []

    def base(evt: str, direction: str, t: int) -> dict[str, Any]:
        return {
            "v": 1,
            "id": f"{symbol}-{profile}-{t}-{evt}-{direction}",
            "symbol": symbol,
            "profile": profile,
            "tf": tf,
            "bar_time_ms": t,
            "event": evt,
            "direction": direction,
        }

    for b in bars:
        for done in htf_agg.push(b):
            htf_mso.push(done)
        mso_events = mso.push(b)
        snap = mso.last
        mso_fields = None
        if snap is not None:
            mso_fields = {
                "trend": snap.trend,
                "osc": None if snap.osc is None else str(round(snap.osc, 2)),
                "htf_trend": htf_mso.trend,
                "confirm_time_ms": b.close_ms,
                "div": None,
            }
        hb = base("HEARTBEAT", "NONE", b.close_ms)
        hb["price"] = {"o": str(b.o), "h": str(b.h), "l": str(b.l), "c": str(b.c), "v": str(b.v)}
        out.append(hb)
        for fe_ev in fe.push(b):
            p = base(fe_ev.event, fe_ev.direction, fe_ev.time_ms)
            p["fractal"] = _fractal_dict(fe_ev.fields)
            out.append(p)
        for me in mso_events:
            p = base(me.event, me.direction, me.confirm_time_ms)
            assert mso_fields is not None
            p["mso"] = {
                **mso_fields,
                "confirm_time_ms": me.confirm_time_ms,
                "div": ("BULL" if me.direction == "LONG" else "BEAR") if me.event == "MSO_DIV" else None,
            }
            out.append(p)
    return out


@dataclass
class ParityReport:
    matched: int = 0
    only_python: list[str] = field(default_factory=list)
    only_bridge: list[str] = field(default_factory=list)
    field_mismatches: list[str] = field(default_factory=list)
    sessions: set[str] = field(default_factory=set)

    @property
    def clean(self) -> bool:
        return not (self.only_python or self.only_bridge or self.field_mismatches)

    def passed(self, min_sessions: int = 20) -> bool:
        return self.clean and len(self.sessions) >= min_sessions


def _key(p: dict[str, Any]) -> str:
    return f"{p['symbol']}|{p['profile']}|{p['event']}|{p['direction']}|{p['bar_time_ms']}"


def _dec(x: Any) -> Decimal | None:
    return None if x is None else Decimal(str(x))


def compare(
    python: Iterable[dict[str, Any]], bridge: Iterable[dict[str, Any]], include_heartbeats: bool = False
) -> ParityReport:
    rep = ParityReport()
    keep = (lambda p: True) if include_heartbeats else (lambda p: p["event"] != "HEARTBEAT")
    a = {_key(p): p for p in python if keep(p)}
    b = {_key(p): p for p in bridge if keep(p)}
    for k in sorted(a.keys() - b.keys()):
        rep.only_python.append(k)
    for k in sorted(b.keys() - a.keys()):
        rep.only_bridge.append(k)
    for k in sorted(a.keys() & b.keys()):
        pa, pb = a[k], b[k]
        rep.sessions.add(session_date(datetime.fromtimestamp(pa["bar_time_ms"] / 1000).astimezone()).isoformat())
        bad = []
        fa, fb = pa.get("fractal") or {}, pb.get("fractal") or {}
        for f in PRICE_KEYS:
            va, vb = _dec(fa.get(f)), _dec(fb.get(f))
            tol = ATR_TOL if f == "htf_atr14" else Decimal(0)
            if (va is None) != (vb is None) or (va is not None and vb is not None and abs(va - vb) > tol):
                bad.append(f)
        bad += [f for f in EXACT_KEYS if fa.get(f) != fb.get(f)]
        ma, mb = pa.get("mso") or {}, pb.get("mso") or {}
        if ma.get("trend") != mb.get("trend") or ma.get("div") != mb.get("div"):
            bad.append("mso.trend/div")
        oa, ob = _dec(ma.get("osc")), _dec(mb.get("osc"))
        if oa is not None and ob is not None and abs(oa - ob) > OSC_TOL:
            bad.append("mso.osc")
        if bad:
            rep.field_mismatches.append(f"{k}: {', '.join(bad)}")
        else:
            rep.matched += 1
    return rep
