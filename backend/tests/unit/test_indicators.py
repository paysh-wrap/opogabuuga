from decimal import Decimal as D

from app.indicators.atr import WilderATR
from app.indicators.bars import MINUTE_MS, Bar, HtfAggregator, round_tick, tf_minutes
from app.indicators.bigbeluga_mso import MsoEngine
from app.indicators.lunqfx_fractal import FractalEngine

T0 = 1_762_354_800_000  # 2025-11-05 15:00:00 UTC — aligned to 15 and 60 minutes
TICK = D("0.25")


def mk(i, o, h, l, c, tf=1):  # noqa: E741
    start = T0 + i * tf * MINUTE_MS
    return Bar(start, start + tf * MINUTE_MS, D(str(o)), D(str(h)), D(str(l)), D(str(c)))


def c1_bars():
    """15 one-minute bars forming C1 with range 100–110."""
    bars = [mk(i, 105, 106, 104, 105) for i in range(15)]
    bars[3] = mk(3, 105, 110, 104, 106)
    bars[9] = mk(9, 105, 106, 100, 104)
    return bars


def run(engine, bars):
    out = []
    for b in bars:
        out += [(e.event, e.direction, (e.time_ms - T0) // MINUTE_MS, e) for e in engine.push(b)]
    return out


def long_model_c2():
    """C2: bearish run from 105, sweep to 99, CISD close above 105, T1 (105) touched, closes 107 inside C1."""
    b = [
        mk(15, 105, 105.5, 103, 103),
        mk(16, 103, 103.5, 101, 101),
        mk(17, 101, 101.5, 99, 99.5),
        mk(18, 99.5, 104, 99.5, 104),
        mk(19, 104, 106, 103.5, 105.5),
    ]
    b += [mk(i, 105.5, 106.5, 105, 106) for i in range(20, 29)]
    b += [mk(29, 106, 107.5, 105.5, 107)]
    return b


def test_tf_and_round():
    assert tf_minutes("1") == 1 and tf_minutes("60") == 60 and tf_minutes("1H") == 60
    assert round_tick(D("105.13"), TICK) == D("105.25") and round_tick(D("105.12"), TICK) == D("105.00")


def test_htf_aggregation_and_late_close():
    agg = HtfAggregator(15)
    done = [x for b in c1_bars() for x in agg.push(b)]
    assert len(done) == 1 and (done[0].h, done[0].l, done[0].close_ms) == (D(110), D(100), T0 + 15 * MINUTE_MS)
    agg = HtfAggregator(15)
    bars = c1_bars()[:-1] + [mk(15, 105, 106, 104, 105)]  # minute 14 missing
    done = [x for b in bars for x in agg.push(b)]
    assert len(done) == 1 and done[0].open_ms == T0  # closed late by the next period's first bar


def test_atr_wilder():
    a = WilderATR(3)
    vals = [a.push(mk(i, 10, 12, 9, 11)) for i in range(4)]
    assert vals[:2] == [None, None] and vals[2] == D(3) and vals[3] == D(3)


def test_long_model_full_lifecycle():
    e = FractalEngine(15, TICK)
    c3 = [mk(30, 107, 108, 106.5, 107.5), mk(31, 107.5, 110.25, 107, 110)]
    c3 += [mk(i, 110, 110.5, 109.5, 110) for i in range(32, 45)]
    ev = run(e, c1_bars() + long_model_c2() + c3)
    names = [(n, d, t) for n, d, t, _ in ev if n != "C1_SWEPT" or d == "LONG"]
    assert ("C1_SWEPT", "LONG", 18) in names  # bar 17 closes at minute 18
    assert ("CISD", "LONG", 20) in names  # bar 19 closes 105.5 > 105 (bear run opened at 105)
    conf = next(x for x in ev if x[0] == "MODEL_CONFIRMED")
    f = conf[3].fields
    assert conf[1:3] == ("LONG", 30)
    assert (f.c1_high, f.c1_low, f.t1, f.t2, f.invalid) == (D(110), D(100), D(105), D(110), D(99))
    assert f.cisd_before_c2_close is True and f.t1_preticked is True and f.cisd_level == D(105)
    assert f.c1_time_ms == T0 and f.c3_close_time_ms == T0 + 45 * MINUTE_MS and f.sweep_time_ms == T0 + 18 * MINUTE_MS
    later = [(n, t) for n, d, t, _ in ev if t > 30 and d == "LONG"]
    assert later == [("T1_HIT", 31), ("T2_HIT", 32), ("C3_CLOSED", 45)]


def weak_long_c2():
    """C2 sweeps to 99 but stays below T1 (105) and never prints CISD; closes 103.5 inside C1."""
    return long_model_c2()[:4] + [mk(i, 104, 104.5, 103, 103.5) for i in range(19, 30)]


def test_model_failed_when_invalid_breaks_before_t1():
    e = FractalEngine(15, TICK)
    c3 = [mk(30, 103.5, 104, 101, 101.5), mk(31, 101.5, 102, 98.75, 99)]  # trades below 99 (invalid), T1 untouched
    c3 += [mk(i, 99, 100, 98.5, 99) for i in range(32, 45)]
    ev = run(e, c1_bars() + weak_long_c2() + c3)
    conf = next(x for x in ev if x[0] == "MODEL_CONFIRMED")[3].fields
    assert conf.cisd_before_c2_close is False and conf.t1_preticked is False
    assert ("MODEL_FAILED", "LONG", 32) in [(n, d, t) for n, d, t, _ in ev]
    assert not any(n == "T1_HIT" for n, *_ in ev)


def test_cisd_during_c3_is_flagged_not_before_c2_close():
    e = FractalEngine(15, TICK)
    c3 = [mk(30, 103.5, 105.5, 103.5, 105.25)] + [mk(i, 105, 105.5, 104.5, 105) for i in range(31, 45)]
    ev = run(e, c1_bars() + weak_long_c2() + c3)
    cisd = [x for x in ev if x[0] == "CISD"]
    assert len(cisd) == 1 and cisd[0][2] == 31 and cisd[0][3].fields.cisd_before_c2_close is False


def test_same_bar_t1_and_invalid_counts_as_failed():
    e = FractalEngine(15, TICK)
    c3 = [mk(30, 102, 105.5, 98.5, 103)] + [mk(i, 103, 104, 102, 103) for i in range(31, 45)]
    ev = run(e, c1_bars() + long_model_c2() + c3)
    assert ("MODEL_FAILED", "LONG", 31) in [(n, d, t) for n, d, t, _ in ev]
    assert not any(n == "T1_HIT" for n, *_ in ev)


def test_no_model_when_c2_closes_outside_c1():
    e = FractalEngine(15, TICK)
    c2 = long_model_c2()[:-1] + [mk(29, 106, 111, 105.5, 110.5)]  # closes above C1 high
    ev = run(e, c1_bars() + c2)
    assert not any(n == "MODEL_CONFIRMED" for n, *_ in ev)


def test_no_model_when_both_sides_swept():
    e = FractalEngine(15, TICK)
    c2 = long_model_c2()
    c2[6] = mk(21, 105.5, 111, 105, 106)  # also sweeps the high
    ev = run(e, c1_bars() + c2)
    assert {(n, d) for n, d, *_ in ev if n == "C1_SWEPT"} == {("C1_SWEPT", "LONG"), ("C1_SWEPT", "SHORT")}
    assert not any(n == "MODEL_CONFIRMED" for n, *_ in ev)


def test_short_model_mirror():
    e = FractalEngine(15, TICK)
    flip = lambda b: Bar(b.open_ms, b.close_ms, 210 - b.o, 210 - b.l, 210 - b.h, 210 - b.c)  # noqa: E731
    ev = run(e, [flip(b) for b in c1_bars() + long_model_c2()])
    conf = next(x for x in ev if x[0] == "MODEL_CONFIRMED")
    f = conf[3].fields
    assert conf[1] == "SHORT" and (f.t1, f.t2, f.invalid, f.cisd_level) == (D(105), D(100), D(111), D(105))


def _bars_from_closes(closes, highs=None, lows=None):
    out = []
    for i, c in enumerate(closes):
        h = highs[i] if highs else c + 0.5
        lo = lows[i] if lows else c - 0.5
        out.append(mk(i, c, h, lo, c, tf=5))
    return out


def test_divergence_on_oscillator_pivots_stamped_at_confirmation_bar():
    import math

    closes = [100 + 10 * math.sin(i / 3) + i * 0.8 for i in range(80)]
    m = MsoEngine(pivot_left=3, pivot_right=3, mom_length=4, smooth_length=2, div_left=2, div_right=2)
    raws, evs = [], []
    for i, b in enumerate(_bars_from_closes([round(c, 2) for c in closes])):
        evs += [(i, e) for e in m.push(b) if e.event == "MSO_DIV"]
        raws.append(m.last.raw)
    assert evs, "expected at least one divergence"
    for i, e in evs:
        j = i - 2  # pivot bar = confirmation bar − right bars
        assert e.confirm_time_ms == mk(i, 0, 0, 0, 0, tf=5).close_ms
        win = raws[j - 2 : j + 3]
        if e.direction == "SHORT":
            assert all(win[2] > x for x in win[:2]) and all(win[2] >= x for x in win[3:])
        else:
            assert all(win[2] < x for x in win[:2]) and all(win[2] <= x for x in win[3:])


def test_structure_choch_then_bos_counts_and_osc_side():
    closes = [
        10,
        11,
        12,
        13,
        14,
        15,
        14,
        13,
        12,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        16,
        15,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        19,
        18,
        17,
        16,
        15,
        14,
        13,
        12,
        11,
        10,
        9,
        8,
        7,
    ]
    m = MsoEngine(pivot_left=2, pivot_right=2, mom_length=3, smooth_length=2, div_left=2, div_right=2)
    evs, snaps = [], []
    for b in _bars_from_closes(closes):
        evs += [(e.event, e.direction) for e in m.push(b) if e.event != "MSO_DIV"]
        snaps.append(m.last)
    assert evs[0] == ("MSO_CHOCH", "LONG")  # first break in a direction = ChoCh (original's count ≤ 1)
    assert ("MSO_BOS", "LONG") in evs  # a second consecutive bullish break = BoS
    assert ("MSO_CHOCH", "SHORT") in evs
    for s in snaps:
        if s.osc is not None:
            assert (s.osc >= 50) if s.trend == "BULL" else (s.osc <= 50)


def test_oscillator_formula_matches_original():
    m = MsoEngine(mom_length=2, smooth_length=1)
    for i, c in enumerate([10, 12, 15]):
        m.push(mk(i, c, c, c, c))
    # roc = 15 − 10 = 5; changes [2, 3] → mean 2.5, pop stdev 0.5; raw = 10; sigmoid = 100/(1+e^-10)
    assert abs(m.last.raw - D(100) / (1 + D(-10).exp())) < D("1e-20")
