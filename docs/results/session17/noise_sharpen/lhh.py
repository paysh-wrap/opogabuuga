"""Candidate 7: last-half-hour momentum on MNQ (one trade/day, enter 15:30 bar open, flat 16:00 close, $250 emergency stop, 1 micro, same costs),
as a 2nd stream beside NOISE (N1 stream). Signal variant picked on IS only. writes lhh.json, streams/LHH.csv, streams/N1_PLUS_LHH.csv"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, "/home/user/opogabuuga/docs/results/session15")
import numpy as np, pandas as pd
import sharpen as S, lib, account as A
from multiprocessing import Pool

SIGS = {"first-30min return": lambda a, o0, pc: a["close"][29] - o0, "open-to-15:29 return": lambda a, o0, pc: a["close"][359] - o0,
        "prior-close-to-15:29 return": lambda a, o0, pc: a["close"][359] - pc}


def lhh(sig, mult, stop_usd=250.0):
    I = lib.INST["MNQ"]; Dd, nb = lib.days("MNQ"); hard = (stop_usd - I["fee"] - 2 * I["tick"] * I["pv"]) / I["pv"]; out = []
    for i in range(14, len(Dd)):
        d, a = Dd[i]
        if d < S.START or d > S.END: continue
        pc = Dd[i - 1][1]["close"][nb - 1]
        if np.isnan(pc) or abs(a["open"][0] / pc - 1) > 0.015 or np.isnan(a["open"][360]): continue
        r = SIGS[sig](a, a["open"][0], pc)
        if not np.isfinite(r) or r == 0: continue
        s = mult * (1 if r > 0 else -1)
        pnl, xk, mae, risk = lib.walk(a, s, 360, hard, None, nb, "MNQ")
        out.append(dict(d=d, ek=360, xk=xk, pnl=pnl, mae=mae, risk=risk, side=s))
    return pd.DataFrame(out)


def acct(a):
    name, t = a
    return name, A.full(lib.day_table(t), lib.plan_rules("150K"), dict(q=3, brake=(0.5, 1)), dict(q=3, brake=(0.5, 1)))


if __name__ == "__main__":
    lib.days("MNQ"); res = {}; st = {}
    for sg in SIGS:
        for m, nm in ((1, "continuation"), (-1, "reversal")):
            t = lhh(sg, m); st[(sg, nm)] = t
            res[f"{sg} / {nm}"] = {e: S.stats(t, e) for e in ("IS", "HO", "L12")}
    # IS-only pick: best IS PF with IS net > 0 and >= 100 trades
    best = max(((v["IS"]["pf"], k) for k, v in res.items() if v["IS"]["net"] > 0 and v["IS"]["n"] >= 100), default=None)
    pick = best[1] if best else None
    out = dict(variants=res, pick=pick)
    n1 = pd.read_csv(HERE + "/streams/BASE__lock_100__10_.csv", dtype={"d": str}) if os.path.exists(HERE + "/streams/BASE__lock_100__10_.csv") else None
    if pick and n1 is not None:
        sg, nm = pick.split(" / "); t = st[(sg, nm)]; t.to_csv(HERE + "/streams/LHH.csv", index=False)
        dn = n1.groupby("d").pnl.sum(); dl = t.groupby("d").pnl.sum()
        alld = pd.bdate_range(S.START, S.END).strftime("%Y-%m-%d")
        x = pd.DataFrame({"n": dn.reindex(alld).fillna(0), "l": dl.reindex(alld).fillna(0)})
        cor = {}
        for era, msk in (("ALL", x.index > "0"), ("IS", x.index <= S.SPLIT), ("HO", x.index > S.SPLIT)):
            y = x[msk]; both = y[(y.n != 0) & (y.l != 0)]
            cor[era] = dict(corr_all_days=float(y.n.corr(y.l)), corr_days_both_trade=float(both.n.corr(both.l)), n_both=int(len(both)),
                            noise_days=int((y.n != 0).sum()), lhh_days=int((y.l != 0).sum()))
        out["corr"] = cor
        mg = A.merge(n1, t); mg.to_csv(HERE + "/streams/N1_PLUS_LHH.csv", index=False)
        out["merged"] = {e: S.stats(mg, e) for e in ("IS", "HO", "L12")}
        out["dropped_overlap"] = int(len(n1) + len(t) - len(mg))
        with Pool(2) as p: out["acct"] = dict(p.map(acct, [("N1 + LHH", mg), ("LHH alone", t)]))
    json.dump(out, open(HERE + "/lhh.json", "w"), indent=1, default=float)
    print(json.dumps({k: (v["IS"]["pf"], v["HO"]["pf"], v["HO"]["net"]) for k, v in res.items()}, indent=1), pick)
