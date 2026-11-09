"""D55 NOISE strategy: pure engine rules + trade-for-trade parity with the research script that was verified on
Databento 2019–2026 (docs/results/tools/noise_area.py)."""

from __future__ import annotations

import importlib.util
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from pathlib import Path

import pytest

from app.backtest.noise_sim import Bar1m, simulate
from app.config import NoiseCfg
from app.engine.noise import (
    Session,
    bands,
    decide,
    hhmm_to_k,
    is_check,
    minute_index,
    plan,
    roll_guard,
    sigma,
    vwap,
)
from app.engine.trade_plan import Direction

REPO = Path(__file__).resolve().parents[3]


def test_minute_index_and_checks():
    # bar closing 10:00 ET (15:00 UTC in November) has k = 29
    assert minute_index(datetime(2026, 11, 9, 15, 0, tzinfo=UTC)) == 29
    assert hhmm_to_k("09:31") == 0 and hhmm_to_k("16:00") == 389
    hourly = [k for k in range(390) if is_check(k, 60, "10:00", "15:30")]
    assert hourly == [29, 89, 149, 209, 269, 329]  # 10:00 … 15:00
    half = [k for k in range(390) if is_check(k, 30, "10:00", "15:30")]
    assert half[0] == 29 and half[-1] == 359 and len(half) == 12


def _sess(day, opn, closes):
    return Session(day, D(opn), {k: D(v) for k, v in closes.items()})


def test_sigma_needs_enough_complete_sessions():
    full = {k: 100 for k in range(390)}
    hist = [_sess(f"d{i}", 100, {**full, 29: 101}) for i in range(9)]
    assert sigma(hist, 29, 14, 10, 300) is None  # 9 sessions < min 10
    hist.append(_sess("d9", 100, {**full, 29: 99}))
    assert sigma(hist, 29, 14, 10, 300) == D("0.01")  # |±1%| averaged
    hist.append(_sess("gap", 100, {0: 100, 29: 150}))  # incomplete session is ignored
    assert sigma(hist, 29, 14, 10, 300) == D("0.01")
    assert sigma(hist, 500, 14, 10, 300) is None  # no session has that minute


def test_bands_roll_guard_vwap():
    b = bands(D(100), D(101), D("0.01"))
    assert b.upper == D("102.01") and b.lower == D("99.00")
    assert roll_guard(D(100), D(101), D("0.015")) and not roll_guard(D(100), D(103), D("0.015"))
    assert not roll_guard(D(100), D(0), D("0.015"))
    assert vwap([(D(3), D(1), D(2), D(10)), (D(5), D(3), D(4), D(30))]) == D("3.5")
    assert vwap([(D(3), D(1), D(2), D(0))]) is None


def test_decide_entries_exits_and_reversal():
    b = bands(D(100), D(100), D("0.01"))  # 101 / 99
    kw = {"k": 29, "b": b, "entries_today": 0, "max_entries": 3, "allow_entry": True}
    assert decide(close=D("101.5"), vw=D(100), position=None, **kw)[0].direction is Direction.LONG
    assert decide(close=D("98.5"), vw=D(100), position=None, **kw)[0].direction is Direction.SHORT
    assert decide(close=D(100), vw=D(100), position=None, **kw)[0].reason == "INSIDE_NOISE_AREA"
    # long: trail = max(upper, vwap); below VWAP but above the band → exit AND re-enter long
    acts = decide(close=D("101.5"), vw=D(102), position=Direction.LONG, **kw)
    assert [a.kind for a in acts] == ["EXIT", "ENTER"] and acts[1].direction is Direction.LONG
    # long below the lower band → exit and reverse short
    acts = decide(close=D("98.5"), vw=D(100), position=Direction.LONG, **kw)
    assert [(a.kind, a.direction) for a in acts] == [("EXIT", Direction.LONG), ("ENTER", Direction.SHORT)]
    assert decide(close=D("101.5"), vw=D(100), position=Direction.LONG, **kw)[0].reason == "HOLD"
    # short trail = min(lower, vwap); no VWAP → band only
    assert decide(close=D("99.5"), vw=None, position=Direction.SHORT, **kw)[0].reason == "NOISE_TRAIL"
    assert decide(close=D("98.5"), vw=None, position=Direction.SHORT, **kw)[0].reason == "HOLD"
    assert decide(close=D("98.5"), vw=D(98), position=Direction.SHORT, **kw)[0].reason == "NOISE_TRAIL"
    assert decide(close=D("101.5"), vw=None, position=Direction.LONG, **kw)[0].reason == "HOLD"
    # 16:00 bar flattens; entry limits respected
    assert decide(close=D(100), vw=None, position=Direction.SHORT, **{**kw, "k": 389})[0].reason == "NOISE_FLAT_1600"
    assert decide(close=D(102), vw=None, position=None, **{**kw, "entries_today": 3})[0].reason == "NO_ENTRY"
    assert decide(close=D(102), vw=None, position=None, **{**kw, "allow_entry": False})[0].reason == "NO_ENTRY"
    assert decide(close=D(102), vw=None, position=None, **{**kw, "k": 389})[0].reason == "NO_ENTRY"
    assert [a.kind for a in decide(close=D("99.5"), vw=D(100), position=Direction.LONG, **kw)] == ["EXIT"]


def test_plan_brackets():
    p = plan(Direction.LONG, D("27000.00"), D("0.25"), D("0.01"), D("0.10"))
    assert p.stop == D("26730.00") and p.take_profit == D("29700.00") and p.risk_pts == D("270.00")
    s = plan(Direction.SHORT, D("27000.10"), D("0.25"), D("0.01"), D("0.10"))
    assert s.stop > D("27000.10") and (s.stop / D("0.25")) % 1 == 0 and s.take_profit < D("27000.10")
    assert s.rr == D("10.00") or s.rr == D("9.99") or s.rr == D("10.01")


# ---------------- parity with the research script ----------------
def _synthetic(n_days=40, seed=7):
    """Trending + choppy random-walk RTH days of 1-minute bars (UTC timestamps, November → ET = UTC−5)."""
    rnd = random.Random(seed)
    px = 20000.0
    days = []
    start = datetime(2026, 1, 5, 14, 30, tzinfo=UTC)  # 09:30 ET (EST)
    d = start
    for i in range(n_days):
        while d.weekday() >= 5:
            d += timedelta(days=1)
        drift = rnd.choice([-1, 0, 0, 1]) * rnd.uniform(0.5, 2.0)
        px *= 1 + rnd.uniform(-0.004, 0.004)  # overnight gap (< 1.5%)
        bars = []
        for k in range(390):
            o = px
            px = max(1000.0, px + drift + rnd.gauss(0, 6))
            h = max(o, px) + abs(rnd.gauss(0, 2))
            lo = min(o, px) - abs(rnd.gauss(0, 2))
            q = lambda x: round(x * 4) / 4  # noqa: E731 - tick 0.25
            bars.append((d + timedelta(minutes=k), q(o), q(h), q(lo), q(px), rnd.randint(50, 500)))
        days.append(bars)
        d += timedelta(days=1)
    return days


class _Pts:  # research trick: pos * hard * entry == pos * PTS (fixed-point emergency stop)
    def __init__(self, p):
        self.p = p

    def __bool__(self):
        return True

    def __rmul__(self, pos):
        return _PV(pos * self.p)


class _PV:
    def __init__(self, v):
        self.v = v

    def __mul__(self, _entry):
        return self.v


@pytest.mark.parametrize("stop_usd", [None, D(250)])  # D58: 1% (verified) and the fixed $250 stop
def test_parity_with_research_script(tmp_path, stop_usd):
    pytest.importorskip("pandas")
    pytest.importorskip("numpy")
    spec = importlib.util.spec_from_file_location("noise_area", REPO / "docs/results/tools/noise_area.py")
    na = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(na)
    days = _synthetic()
    csv = tmp_path / "mnq.csv"
    with csv.open("w") as f:
        f.write("timestamp,open,high,low,close,volume\n")
        for bars in days:
            for t, o, h, lo, c, v in bars:
                f.write(f"{t.strftime('%Y-%m-%dT%H:%M:%SZ')},{o},{h},{lo},{c},{v}\n")
    hard = 0.01 if stop_usd is None else _Pts(float((stop_usd - 2) / 2))
    research = na.run(na.load_days(str(csv)), look=14, step=60, hard=hard, maxtr=3)
    sim_days = [
        (
            bars[0][0].astimezone().date().isoformat() if False else bars[0][0].date().isoformat(),
            [Bar1m(k, D(str(o)), D(str(h)), D(str(lo)), D(str(c)), D(v)) for k, (_, o, h, lo, c, v) in enumerate(bars)],
        )
        for bars in days
    ]
    cfg = NoiseCfg(
        min_history_days=14, emergency_stop_usd=stop_usd
    )  # the research script needs 14 complete days before its first trade
    ours = simulate(sim_days, cfg, tick=D("0.25"), point_value=D(2), fee_rt=D(1))
    assert len(research) > 10, "synthetic data must produce trades"
    assert len(ours) == len(research)
    for (_, r), t in zip(research.iterrows(), ours, strict=True):
        assert str(r.d) == t.day
        assert int(r.side) == t.direction.sign
        assert float(t.entry) == pytest.approx(r.entry, abs=1e-6)
        assert float(t.exit) == pytest.approx(r.exit, abs=1e-6)
        assert float(t.pnl) == pytest.approx(r.pnl, abs=1e-6)
