"""ORDER FLOW · AUCTION (IMRE) engine (D150): one test per rule id of docs/IMRE_AMT_RULES.md that is built."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal as D

from app.config import AuctionImreCfg
from app.engine import auction_imre as A
from app.engine.conti_orb import MBar
from app.engine.trade_plan import Direction

TICK = D("0.25")
CFG = AuctionImreCfg(enabled=True)
PRIOR = [(100, 110, 90, 100, 1000)] * 3 + [(100, 100, 100, 100, 3000), (90, 90, 80, 85, 10), (110, 120, 110, 115, 10)]
BG = [(100, 100.25, 99.75, 100.25, 10)] * 20  # quiet bars: small estimated delta


def day(d, rows):
    t0 = datetime(2026, 10, d, 9, 30, tzinfo=A.ET)
    return [MBar(t0 + timedelta(minutes=i + 1), *(D(str(x)) for x in r)) for i, r in enumerate(rows)]


def hist(older=(90, 120, 80, 100, 100)):  # default: today's prior day sits inside the older one → BALANCE
    return day(9, [older]) + day(12, PRIOR)


def test_a2_a3_one_time_framing_strict():
    up = [(0, D(100), D(80), D(90)), (0, D(110), D(85), D(95))]
    assert A.one_time_framing(up) == "OTFU"
    dn = [(0, D(110), D(85), D(95)), (0, D(100), D(80), D(90))]
    assert A.one_time_framing(dn) == "OTFD"
    assert A.one_time_framing([(0, D(110), D(85), D(95)), (0, D(111), D(86), D(95))]) == "BALANCE"  # no higher close
    assert A.one_time_framing(up[:1]) == "NO_HISTORY"
    assert A.replay_day(hist(), day(13, BG), CFG, TICK).regime == "BALANCE"
    assert A.replay_day(hist((95, 100, 75, 95, 100)), day(13, BG), CFG, TICK).regime == "OTFU"


def test_b1_profile_poc_value_area_and_lvn():
    p = A.profile(day(12, PRIOR), D("0.7"), D("0.3"), TICK)
    assert (p.poc, p.val, p.vah) == (D(100), D(96), D(104))
    gap = [(100, 104, 96, 100, 100), (100, 104, 103, 103.5, 900), (100, 97, 96, 96.5, 900)]
    assert A.profile(day(12, gap), D("0.9"), D("0.5"), TICK).lvns  # thin middle = low-volume nodes
    assert A.profile([], D("0.7"), D("0.3"), TICK) is None


def test_b7_open_vs_prior_value():
    assert A.replay_day(hist(), day(13, BG), CFG, TICK).open_vs_value == "INSIDE"
    assert A.replay_day(hist(), day(13, [(110, 110, 110, 110, 1)]), CFG, TICK).open_vs_value == "ABOVE"
    assert A.replay_day(hist(), day(13, [(90, 90, 90, 90, 1)]), CFG, TICK).open_vs_value == "BELOW"
    assert A.replay_day([], day(13, BG), CFG, TICK).prior is None


def test_c4_c5_estimated_delta_and_big_bubble():
    assert A.est_delta(MBar(datetime.now(A.ET), D(1), D(1), D(1), D(1), D(5))) == 0
    bars = day(13, [*BG, (100, 101, 100, 101, 100), (101, 101, 100, 100.25, 100), (100, 100.5, 99.5, 100.5, 10)])
    assert A.bubble(bars, 20, CFG) == 1 and A.bubble(bars, 21, CFG) == -1 and A.bubble(bars, 22, CFG) == 0
    assert A.bubble(bars, 0, CFG) == 0
    wick = day(13, [*BG, (100, 102, 99, 100.5, 100)])  # buying delta but… still closes up → +1
    assert A.bubble(wick, 20, CFG) == 1


def test_d2_d3_d4_d5_failed_auction_v_long():
    today = day(13, [*BG, (97, 97, 95, 95.25, 100), (95.25, 96.75, 95, 96.5, 100)])
    [s] = A.replay_day(hist(), today, CFG, TICK).signals
    assert (s.setup, s.direction, s.entry, s.stop) == ("FAILED_AUCTION_V", Direction.LONG, D("96.5"), D("94.5"))
    assert (s.tp1, s.tp2, s.risk_share) == (D(100), D(104), D(1))


def test_d8_failed_auction_v_short_mirror():
    today = day(13, [*BG, (103, 105, 103, 104.75, 100), (104.75, 105, 103.25, 103.5, 100)])
    [s] = A.replay_day(hist(), today, CFG, TICK).signals
    assert s.direction == Direction.SHORT and s.stop == D("105.5") and (s.tp1, s.tp2) == (D(100), D(96))


def test_f7_min_reward_to_the_first_target():
    today = day(13, [*BG, (97, 97, 95, 95.25, 100), (95.25, 97.75, 95, 97.5, 100)])
    assert A.replay_day(hist(), today, CFG, TICK).signals == []


def test_d6_d7_slow_flavour_plan_b_and_plan_a():
    base = [*BG, (103.5, 104.75, 103.5, 104.5, 10), (104.5, 104.5, 103.5, 103.75, 10)]
    micro = [(103.75, 104, 103.5, 103.75, 10)] * 5
    [b] = A.replay_day(hist(), day(13, [*base, *micro, (103.75, 103.75, 102.75, 102.75, 100)]), CFG, TICK).signals
    assert (b.setup, b.direction, b.entry, b.stop, b.risk_share) == (
        "FAILED_AUCTION_SLOW_B", Direction.SHORT, D("102.75"), D("104.5"), D("0.5"))  # fmt: skip
    [a] = A.replay_day(hist(), day(13, [*base, *micro, (103.75, 104.25, 103.5, 103.5, 100)]), CFG, TICK).signals
    assert a.setup == "FAILED_AUCTION_SLOW_A" and a.stop == D("104.75") and a.risk_share == D("0.5")


def test_e1_e2_e3_breakout_plan_a_only_in_imbalance():
    up = hist((95, 100, 75, 95, 100))
    brk = [*BG, (103.75, 104.5, 103.75, 104.25, 10)]
    micro = [(104.5, 105, 104.25, 104.5, 10)] * 5
    [s] = A.replay_day(up, day(13, [*brk, *micro, (104.5, 105.25, 104, 105, 100)]), CFG, TICK).signals
    assert (s.setup, s.direction, s.entry, s.stop, s.tp1) == ("BREAKOUT_A", Direction.LONG, D(105), D("103.5"), D(108))
    assert A.replay_day(up, day(13, [*BG, (103.75, 106, 103.75, 106, 100)]), CFG, TICK).signals == []  # E1
    bal = A.replay_day(hist(), day(13, [*brk, *micro, (104.5, 105.25, 104, 105, 100)]), CFG, TICK)
    assert all(x.setup.startswith("FAILED") for x in bal.signals)  # A4: no breakouts in balance


def test_e4_e5_breakout_plan_b_split_risk():
    up = hist((95, 100, 75, 95, 100))
    rows = [
        *BG,
        (103.75, 104.5, 103.75, 104.25, 10),
        *[(104.5, 105, 104.25, 104.5, 10)] * 5,
        (104.5, 106, 104.5, 106, 100),
    ]
    [s] = A.replay_day(up, day(13, rows), CFG, TICK).signals
    assert s.setup == "BREAKOUT_B" and s.risk_share == D("0.5") and s.stop == D(104)


def test_e2_micro_range_and_otfd():
    rows = day(13, [(1, 2, 1, 2, 1)] * 3)
    assert A.micro_range(rows, 1, CFG) is None  # too few bars
    wide = day(13, [(100, 130, 90, 100, 1)] * 6)
    assert A.micro_range(wide, 5, CFG) is None
    dn = A.replay_day(hist((110, 125, 85, 125, 100)), day(13, BG), CFG, TICK)
    assert dn.regime == "OTFD"


def test_f4_f8_window_max_trades_and_outcomes():
    v = [*BG, (97, 97, 95, 95.25, 100), (95.25, 96.75, 95, 96.5, 100)]
    early = CFG.model_copy(update={"window": "09:30-09:40"})
    assert A.replay_day(hist(), day(13, v), early, TICK).signals == []
    [s] = A.replay_day(hist(), day(13, [*v, (96.5, 104.5, 96.5, 104, 10)]), CFG, TICK).signals
    assert s.outcome == "TP"
    [s] = A.replay_day(hist(), day(13, [*v, (96.5, 96.5, 94, 94.25, 10)]), CFG, TICK).signals
    assert s.outcome == "STOP"
    one = CFG.model_copy(update={"max_trades_per_day": 1})
    two = [*v, (96.5, 96.5, 94, 94.25, 10), *BG, (97, 97, 95, 95.25, 100), (95.25, 96.75, 95, 96.5, 100)]
    assert len(A.replay_day(hist(), day(13, two), one, TICK).signals) == 1
    assert len(A.replay_day(hist(), day(13, two), CFG, TICK).signals) == 2
