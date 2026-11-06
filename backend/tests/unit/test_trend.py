"""D44 trend filters: incremental VWAP / EMA 200 5m / UT Bot 5m + the TREND gate."""

from decimal import Decimal as D

from app.indicators.trend import FIVE_MIN_MS, TrendState

M = 60_000


def feed(tr, closes, start=0, tf=M, sess=1, vol=D(1)):
    for i, c in enumerate(closes):
        c = D(c)
        tr.update(start + i * tf, tf, sess, c, c + 1, c - 1, c, vol)


def test_warmup_then_uptrend_is_bullish():
    tr = TrendState()
    assert tr.direction() == {"vwap": None, "ema200_5m": None, "utbot_5m": None, "squeeze_5m_15m": None}
    feed(tr, [100 + i * D("0.1") + (i % 7) * D("0.05") for i in range(5 * 210)])
    d = tr.direction()
    assert {k: d[k] for k in ("vwap", "ema200_5m", "utbot_5m")} == {"vwap": 1, "ema200_5m": 1, "utbot_5m": 1}


def test_downtrend_bearish_and_vwap_resets_each_session():
    tr = TrendState()
    feed(tr, [500 - i * D("0.1") for i in range(5 * 210)])
    assert {k: tr.direction()[k] for k in ("vwap", "ema200_5m", "utbot_5m")} == {
        "vwap": -1,
        "ema200_5m": -1,
        "utbot_5m": -1,
    }
    n = 5 * 210
    feed(tr, [10], start=n * M, sess=2)  # new session: VWAP = this bar only (typical price 10 = close) → flat
    assert tr.direction()["vwap"] is None and tr.vwap == D(10)


def test_old_bars_ignored_and_5m_bars_used_directly():
    tr = TrendState()
    feed(tr, [100, 101], tf=FIVE_MIN_MS)
    assert tr.ema200_5m.count == 2
    tr.update(0, FIVE_MIN_MS, 1, D(1), D(1), D(1), D(1), D(1))  # repeated bar → ignored
    assert tr.ema200_5m.count == 2 and tr.last_close == D(101)
    tr.update(2 * FIVE_MIN_MS, 15 * M, 1, D(1), D(2), D(0), D(1), D(0))  # 15m bar: VWAP only (no volume → kept)
    assert tr.ema200_5m.count == 2 and tr.vwap is not None


def test_ut_bot_flip_paths():
    tr = TrendState()
    feed(tr, [100] * 20 + [80] * 15 + [120] * 15, tf=FIVE_MIN_MS)
    assert tr.direction()["utbot_5m"] == 1


def _ref_squeeze(h, lo, c, n=20):
    """Independent float version of LazyBear's momentum (same formulas as docs/results/tools/indscreen.py)."""
    out = []
    ys = []
    for i in range(len(c)):
        if i < n - 1:
            out.append(None)
            continue
        basis = sum(c[i - n + 1 : i + 1]) / n
        ys.append(c[i] - ((max(h[i - n + 1 : i + 1]) + min(lo[i - n + 1 : i + 1])) / 2 + basis) / 2)
        if len(ys) < n:
            out.append(None)
            continue
        w = ys[-n:]
        xm = (n - 1) / 2
        ym = sum(w) / n
        slope = sum((k - xm) * (y - ym) for k, y in enumerate(w)) / sum((k - xm) ** 2 for k in range(n))
        out.append(ym + slope * xm)
    return out


def test_squeeze_matches_float_reference_on_random_walk():
    import random

    from app.indicators.trend import _Squeeze

    rnd = random.Random(7)
    c, h, lo, px = [], [], [], 2000.0
    for _ in range(300):
        px += rnd.uniform(-3, 3)
        c.append(round(px, 1))
        h.append(round(px + rnd.uniform(0, 2), 1))
        lo.append(round(px - rnd.uniform(0, 2), 1))
    ref = _ref_squeeze(h, lo, c)
    sq = _Squeeze()
    for i in range(len(c)):
        sq.update(D(str(h[i])), D(str(lo[i])), D(str(c[i])))
        if ref[i] is None:
            assert sq.val is None
        else:
            assert abs(float(sq.val) - ref[i]) < 1e-9, i
            if i > 0 and ref[i - 1] is not None:
                want = 1 if ref[i] > ref[i - 1] else -1 if ref[i] < ref[i - 1] else 0
                assert sq.rising() == want, i


def test_squeeze_5m_15m_direction_needs_both_to_agree():
    tr = TrendState()
    assert tr.direction()["squeeze_5m_15m"] is None
    up = [100 + i * D("0.2") + (i % 5) * D("0.3") for i in range(15 * 45)]
    feed(tr, up)  # steady climb on 1m bars → 5m and 15m momentum rising
    assert tr.sqz_5m.rising() is not None and tr.sqz_15m.rising() is not None
    want = tr.sqz_5m.rising() if tr.sqz_5m.rising() == tr.sqz_15m.rising() else 0
    assert tr.direction()["squeeze_5m_15m"] == want
    tr.sqz_5m.prev, tr.sqz_5m.val = D(2), D(1)  # 5m falling, 15m not → no side
    if tr.sqz_15m.rising() != -1:
        assert tr.direction()["squeeze_5m_15m"] == 0
    tr.sqz_15m.prev, tr.sqz_15m.val = D(2), D(1)
    assert tr.direction()["squeeze_5m_15m"] == -1
    tr.sqz_15m.prev = D(1)  # flat 15m → 0 → no side
    assert tr.sqz_15m.rising() == 0 and tr.direction()["squeeze_5m_15m"] == 0
