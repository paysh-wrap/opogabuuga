"""Walk-forward ARX model: next-bar return on lagged returns + lagged OFI.

    r_{t+1} = c + sum_{i=0..p-1} phi_i r_{t-i} + sum_{j=0..q-1} beta_j nofi_{t-j} + eps

Everything on the right is known at the close of bar t, so the forecast is
tradeable at t. Fit by ridge-regularised OLS on a rolling window and refit
every `refit` bars. Multi-level OFIs are highly collinear (Xu/Cont et al.),
which is why a ridge penalty is used rather than plain OLS.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class ARXConfig:
    p: int = 3              # return lags (the AR part)
    q: int = 3              # OFI lags (the X part)
    window: int = 2000      # training bars
    refit: int = 250        # bars between refits
    ridge: float = 1e-3     # L2 penalty relative to feature variance
    ofi_col: str = "nofi"


def design(bars: pd.DataFrame, cfg: ARXConfig) -> tuple[pd.DataFrame, pd.Series]:
    """X_t (known at t) and y_t = r_{t+1}."""
    cols = {}
    for i in range(cfg.p):
        cols[f"r_l{i}"] = bars["ret"].shift(i)
    for j in range(cfg.q):
        cols[f"ofi_l{j}"] = bars[cfg.ofi_col].shift(j)
    X = pd.DataFrame(cols, index=bars.index)
    y = bars["ret"].shift(-1).rename("y")
    return X, y


def _fit(X: np.ndarray, y: np.ndarray, ridge: float):
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1.0
    Z = (X - mu) / sd
    ym = y.mean()
    A = Z.T @ Z + ridge * len(Z) * np.eye(Z.shape[1])
    w = np.linalg.solve(A, Z.T @ (y - ym))
    return mu, sd, ym, w


def walk_forward(bars: pd.DataFrame, cfg: ARXConfig = ARXConfig()) -> pd.DataFrame:
    """Out-of-sample predictions. Training rows for a fit at bar t use only
    targets y_s with s < t (i.e. returns realised by the close of bar t)."""
    X, y = design(bars, cfg)
    ok = X.notna().all(axis=1).to_numpy()
    Xv, yv = X.to_numpy(float), y.to_numpy(float)
    n = len(bars)
    pred = np.full(n, np.nan)
    coefs = []
    params = None
    for t in range(cfg.window, n):
        if params is None or (t - cfg.window) % cfg.refit == 0:
            # rows s in [t-window, t-1]: y_s = r_{s+1} is known by close of t
            lo = t - cfg.window
            m = ok[lo:t] & ~np.isnan(yv[lo:t])
            if m.sum() > X.shape[1] + 10:
                params = _fit(Xv[lo:t][m], yv[lo:t][m], cfg.ridge)
                coefs.append((bars.index[t], *(params[3] / params[1])))
        if params is not None and ok[t]:
            mu, sd, ym, w = params
            pred[t] = ym + ((Xv[t] - mu) / sd) @ w
    out = pd.DataFrame({"pred": pred, "y": yv}, index=bars.index)
    out.attrs["coefs"] = pd.DataFrame(
        coefs, columns=["refit_at", *X.columns]
    ).set_index("refit_at")
    return out


def backtest(pred: pd.DataFrame, cost: float, k: float = 1.0) -> dict:
    """Trade sign(pred) only when |pred| > k * cost, else flat.

    cost = one-way cost in log-return units (half-spread + fees + slippage).
    Edge must clear cost -- the Nov-2026 OFI foundation-model paper found
    sub-second forecasts did NOT clear ~2 bps one-way, so this gate matters.
    """
    df = pred.dropna()
    pos = np.where(df["pred"].abs() > k * cost, np.sign(df["pred"]), 0.0)
    turnover = np.abs(np.diff(np.concatenate([[0.0], pos])))
    gross = pos * df["y"].to_numpy()
    net = gross - cost * turnover
    traded = pos != 0
    sd = net.std()
    return {
        "bars": int(len(df)),
        "active_frac": float(traded.mean()) if len(df) else 0.0,
        "hit_rate": float((np.sign(df["y"].to_numpy()[traded]) == pos[traded]).mean())
        if traded.any() else float("nan"),
        "ic": float(np.corrcoef(df["pred"], df["y"])[0, 1]) if len(df) > 2 else float("nan"),
        "gross": float(gross.sum()),
        "net": float(net.sum()),
        "turnover": float(turnover.sum()),
        "sharpe_per_bar": float(net.mean() / sd) if sd > 0 else 0.0,
    }
