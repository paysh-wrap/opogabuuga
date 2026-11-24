"""Order Flow Imbalance (Cont, Kukanov & Stoikov 2014) feature construction.

Input: top-of-book snapshots/updates in time order with columns
    bid_px, bid_sz, ask_px, ask_sz   (Databento MBP-1: *_00 columns, renamed)
indexed by a DatetimeIndex (exchange timestamp, NOT a cumulative dt sum).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

BOOK_COLS = ["bid_px", "bid_sz", "ask_px", "ask_sz"]


def l1_ofi(book: pd.DataFrame) -> pd.Series:
    """Per-event best-level OFI e_n.

    e_n = 1{Pb_n >= Pb_{n-1}} qb_n - 1{Pb_n <= Pb_{n-1}} qb_{n-1}
        - 1{Pa_n <= Pa_{n-1}} qa_n + 1{Pa_n >= Pa_{n-1}} qa_{n-1}
    Positive = net buying pressure. First event is 0.
    """
    missing = set(BOOK_COLS) - set(book.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")
    pb, qb, pa, qa = (book[c].to_numpy(dtype=float) for c in BOOK_COLS)
    e = np.zeros(len(book))
    if len(book) > 1:
        pb0, qb0, pa0, qa0 = pb[:-1], qb[:-1], pa[:-1], qa[:-1]
        pb1, qb1, pa1, qa1 = pb[1:], qb[1:], pa[1:], qa[1:]
        e[1:] = (
            (pb1 >= pb0) * qb1
            - (pb1 <= pb0) * qb0
            - (pa1 <= pa0) * qa1
            + (pa1 >= pa0) * qa0
        )
    return pd.Series(e, index=book.index, name="ofi")


def bar_features(book: pd.DataFrame, freq: str = "1s") -> pd.DataFrame:
    """Aggregate events into clock-time bars.

    Columns:
      ofi   - summed raw OFI in the bar
      depth - mean (bid_sz + ask_sz)/2 in the bar (price-impact slope ~ 1/depth)
      nofi  - ofi / depth  (depth-normalised, comparable across sessions)
      mid   - last mid in the bar
      ret   - log return of mid from previous bar close to this bar close
    Bars with no events are dropped (no forward-filled fake returns).
    """
    df = book[BOOK_COLS].copy()
    df["ofi"] = l1_ofi(book)
    df["mid"] = (df["bid_px"] + df["ask_px"]) / 2.0
    df["dep"] = (df["bid_sz"] + df["ask_sz"]) / 2.0
    g = df.resample(freq)
    bars = pd.DataFrame(
        {
            "ofi": g["ofi"].sum(),
            "depth": g["dep"].mean(),
            "mid": g["mid"].last(),
            "n": g["ofi"].count(),
        }
    )
    bars = bars[bars["n"] > 0].drop(columns="n")
    bars["nofi"] = bars["ofi"] / bars["depth"].replace(0, np.nan)
    bars["ret"] = np.log(bars["mid"]).diff()
    return bars.dropna()
