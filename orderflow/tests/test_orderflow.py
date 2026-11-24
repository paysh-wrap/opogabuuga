import numpy as np
import pandas as pd
import pytest

from orderflow.ofi import l1_ofi, bar_features
from orderflow.arx import ARXConfig, design, walk_forward, backtest


def book(rows):
    idx = pd.date_range("2026-11-02 14:30", periods=len(rows), freq="100ms")
    return pd.DataFrame(rows, columns=["bid_px", "bid_sz", "ask_px", "ask_sz"], index=idx)


def test_l1_ofi_hand_cases():
    b = book([
        [100, 10, 101, 10],   # start
        [100, 15, 101, 10],   # bid size +5      -> +5
        [100, 15, 101, 4],    # ask size -6      -> +6
        [101, 3, 102, 8],     # bid up (new 3), ask up (old ask 4 removed) -> 3 + 4 = +7
        [100, 9, 101, 2],     # bid down (old 3 gone), ask down (new 2)  -> -3 - 2 = -5
    ])
    assert l1_ofi(b).tolist() == [0, 5, 6, 7, -5]


def test_l1_ofi_missing_cols():
    with pytest.raises(ValueError):
        l1_ofi(pd.DataFrame({"bid_px": [1.0]}))


def test_bar_features_drops_empty_bars():
    b = book([[100, 10, 101, 10]] * 5)
    b.index = pd.to_datetime(["2026-11-02 14:30:00.1", "2026-11-02 14:30:00.2",
                              "2026-11-02 14:30:01.1", "2026-11-02 14:30:03.1",
                              "2026-11-02 14:30:03.5"])
    bars = bar_features(b, "1s")
    # bars at :00, :01, :03 ; first dropped by ret diff; :02 empty -> absent
    assert list(bars.index.second) == [1, 3]


def synthetic_bars(n, beta, seed=0):
    rng = np.random.default_rng(seed)
    nofi = rng.standard_normal(n)
    ret = np.zeros(n)
    ret[1:] = beta * nofi[:-1] * 1e-4 + rng.standard_normal(n - 1) * 1e-4
    idx = pd.date_range("2026-11-02", periods=n, freq="1s")
    return pd.DataFrame({"ret": ret, "nofi": nofi}, index=idx)


def test_design_alignment():
    bars = synthetic_bars(10, 0.0)
    X, y = design(bars, ARXConfig(p=2, q=2))
    t = bars.index[5]
    assert X.loc[t, "r_l1"] == bars["ret"].iloc[4]
    assert X.loc[t, "ofi_l0"] == bars["nofi"].iloc[5]
    assert y.loc[t] == bars["ret"].iloc[6]


def test_recovers_lagged_ofi_signal_and_profits():
    bars = synthetic_bars(6000, beta=0.5)
    out = walk_forward(bars, ARXConfig(window=1500, refit=500))
    coefs = out.attrs["coefs"]
    assert (coefs["ofi_l0"] > 0).all()
    assert out.dropna()["pred"].corr(out.dropna()["y"]) > 0.3
    res = backtest(out, cost=0.1e-4)
    assert res["net"] > 0 and res["hit_rate"] > 0.6


def test_no_signal_no_edge_after_costs():
    bars = synthetic_bars(6000, beta=0.0, seed=1)
    out = walk_forward(bars, ARXConfig(window=1500, refit=500))
    res = backtest(out, cost=0.5e-4)
    assert res["net"] <= 0 + 1e-12


def test_no_lookahead():
    bars = synthetic_bars(3000, beta=0.5, seed=2)
    cfg = ARXConfig(window=1000, refit=200)
    a = walk_forward(bars, cfg)["pred"]
    t = 2000
    tampered = bars.copy()
    tampered.iloc[t + 1:, :] = 99.0   # corrupt everything after bar t
    b = walk_forward(tampered, cfg)["pred"]
    pd.testing.assert_series_equal(a.iloc[: t + 1], b.iloc[: t + 1])
