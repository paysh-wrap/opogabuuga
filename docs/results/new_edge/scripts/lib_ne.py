"""new_edge shared lib (research only). MNQ RTH 1-min bars (idx 0 = 09:30 ET, 389 = 15:59), 2021-10..2026-10, cached days.pkl.
No MGC / no overnight data exists in the sandbox (no Databento key) -> MGC and overnight-return variants are NOT testable here."""
import pickle, numpy as np, pandas as pd
PKL = "/tmp/claude-0/-home-user-opogabuuga/a242e4b9-b41b-5028-bba9-c21e825f6a98/scratchpad/data/days.pkl"
D, _ = pickle.load(open(PKL, "rb"))
_ds = [d for d, _a in D]
DAYS = [d for d in _ds if "2021-10-21" <= d <= "2026-10-30"]
BARS = {d: a for d, a in D}
PICK_END = "2023-12-31"; JUDGE0 = "2024-01-01"
COST_PTS = 1.0          # $2 per micro round trip ($1 fee + 1 tick slippage each way); 1 MNQ point = $2 per micro
PV = 2.0
PREV = {d: (BARS[_ds[i - 1]]["close"][-1] if i else np.nan) for i, d in enumerate(_ds)}
RNG = {d: float(BARS[d]["high"].max() - BARS[d]["low"].min()) for d in _ds}
ATR = {d: (float(np.mean([RNG[x] for x in _ds[max(0, i - 14):i]])) if i >= 3 else np.nan) for i, d in enumerate(_ds)}


def run_trade(a, e, side, stop, target, x_end):
    """enter at open of bar e; stop first if both hit; else target; else close of bar x_end."""
    o, h, l, c = a["open"], a["high"], a["low"], a["close"]
    en = o[e]
    for k in range(e, x_end + 1):
        if side == 1:
            if l[k] <= en - stop: return -stop, k
            if target and h[k] >= en + target: return target, k
        else:
            if h[k] >= en + stop: return -stop, k
            if target and l[k] <= en - target: return target, k
    return side * (c[x_end] - en), x_end


def stats(tr):
    out = {}
    for nm, m in (("pick", tr.day <= PICK_END), ("judge", tr.day >= JUDGE0), ("all", tr.day >= "0")):
        t = tr[m]; net = t.pts - COST_PTS
        w = net[net > 0].sum(); ls = -net[net < 0].sum()
        out[nm] = dict(n=int(len(t)), pf=round(float(w / ls), 3) if ls > 0 else None, wr=round(float((net > 0).mean() * 100), 1) if len(t) else None,
                       net_usd_micro=round(float(net.sum() * PV), 0), exp_pts=round(float(net.mean()), 2) if len(t) else None)
    return out
