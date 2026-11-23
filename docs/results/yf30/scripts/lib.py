"""yf30 shared helpers (research only). Run: PYTHONPATH=backend <yfvenv>/bin/python docs/results/yf30/scripts/<script>.py
Data: Yahoo continuous futures (MGC=F, MNQ=F, MES=F), 2-minute bars, 24h incl. overnight, last 30 days (yfinance = OpenBB's
yfinance provider). NOT Databento MGC.v.0 volume-rolled contracts: Yahoo splices the front month (roll jumps possible)."""
from __future__ import annotations
import random
from dataclasses import dataclass
from datetime import time
from decimal import Decimal as D
from pathlib import Path
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
ET = "America/New_York"
# tick, tick_value, fee_rt, slippage ticks (config/rules/lucid_pro_25k.yaml instruments + trade_plan.slippage_ticks)
INST = {"MNQ": (0.25, 0.50, 1.00, 1), "MES": (0.25, 1.25, 1.00, 1), "MGC": (0.10, 1.00, 1.60, 1)}
FILES = {"MNQ": "MNQ_MNQF_2m.csv", "MES": "MES_MESF_2m.csv", "MGC": "MGC_MGCF_2m.csv"}


def load(sym: str) -> pd.DataFrame:
    df = pd.read_csv(DATA / FILES[sym], index_col=0)
    df.index = pd.to_datetime(df.index, utc=True).tz_convert(ET)
    df = df[~df.index.duplicated()].sort_index()[["Open", "High", "Low", "Close", "Volume"]]
    df.columns = ["o", "h", "l", "c", "v"]
    # bar OPEN stamps; close_time = open + 2 min. Drop the still-forming last day (partial).
    last = df.index[-1].date()
    return df[df.index.date != last]


def cost_usd(sym: str) -> float:
    tick, tv, fee, slip = INST[sym]
    return fee + 2 * slip * tv


def pt_usd(sym: str) -> float:
    return INST[sym][1] / INST[sym][0]


def stats(pnls: list[float]) -> dict:
    n = len(pnls)
    if not n:
        return dict(n=0, win=0.0, pf=0.0, net=0.0, avg=0.0)
    w = [p for p in pnls if p > 0]; l = [-p for p in pnls if p < 0]
    pf = (sum(w) / sum(l)) if l else float("inf")
    return dict(n=n, win=round(100 * len(w) / n, 1), pf=round(pf, 2), net=round(sum(pnls), 1), avg=round(sum(pnls) / n, 2))


def sim_path(df, i_start, i_end, entry, sign, stop_pts, tp_pts=None):
    """Walk bars i_start..i_end (positional, inclusive) from `entry`; stop first, then TP; else exit at close of i_end.
    Returns (pts, exit_pos)."""
    stop = entry - sign * stop_pts
    tp = None if tp_pts is None else entry + sign * tp_pts
    H, L, C = df.h.values, df.l.values, df.c.values
    for j in range(i_start, i_end + 1):
        if (L[j] <= stop) if sign > 0 else (H[j] >= stop):
            return (stop - entry) * sign, j
        if tp is not None and ((H[j] >= tp) if sign > 0 else (L[j] <= tp)):
            return (tp - entry) * sign, j
    return (C[i_end] - entry) * sign, i_end


def random_baseline(trades, sym, df, draws=2000, seed=7):
    """Same entry bar, same exit bar, same stop/target distances, coin-flip direction. Returns p-values of the actual
    net $ and PF against the random-direction distribution."""
    rnd = random.Random(seed)
    cu, pu = cost_usd(sym), pt_usd(sym)
    act = stats([t["usd"] for t in trades])
    nets, pfs = [], []
    for _ in range(draws):
        res = []
        for t in trades:
            sgn = rnd.choice((-1, 1))
            pts, _ = sim_path(df, t["i0"], t["i1"], t["entry"], sgn, t["stop_pts"], t.get("tp_pts"))
            res.append(pts * pu - cu)
        s = stats(res); nets.append(s["net"]); pfs.append(s["pf"] if s["pf"] != float("inf") else 99)
    nets.sort(); pfs.sort()
    return dict(rand_net_mean=round(sum(nets) / draws, 1), rand_net_p95=nets[int(.95 * draws)],
                rand_pf_mean=round(sum(pfs) / draws, 2), rand_pf_p95=pfs[int(.95 * draws)],
                p_net=round(sum(1 for x in nets if x >= act["net"]) / draws, 3))
