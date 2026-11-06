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
    assert tr.direction() == {"vwap": None, "ema200_5m": None, "utbot_5m": None}
    feed(tr, [100 + i * D("0.1") for i in range(5 * 210)])
    d = tr.direction()
    assert d == {"vwap": 1, "ema200_5m": 1, "utbot_5m": 1}


def test_downtrend_bearish_and_vwap_resets_each_session():
    tr = TrendState()
    feed(tr, [500 - i * D("0.1") for i in range(5 * 210)])
    assert tr.direction() == {"vwap": -1, "ema200_5m": -1, "utbot_5m": -1}
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
