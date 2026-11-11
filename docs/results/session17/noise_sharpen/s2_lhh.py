"""Last-half-hour momentum add-on on MNQ: one trade/day, enter at the 15:30 bar open (+1 tick), $250 emergency stop, flat on the 15:59 close, same costs.
Three IS-candidate signals x continuation/reversal; variant picked on IS only (best IS PF with IS net > 0 and >= 100 trades).
Then merged with NOISE (preset C base and plain base, one open position per account: an LHH trade is dropped if NOISE is still in a position at 15:30).
Writes lhh.json, streams/LHH*.csv"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, pandas as pd
import nz, sim

SIGS = {"first-30min return": lambda a, o0, pc: a["close_l"][29] - o0, "open-to-15:29 return": lambda a, o0, pc: a["close_l"][359] - o0,
        "prior-close-to-15:29 return": lambda a, o0, pc: a["close_l"][359] - pc}


def lhh(sig, mult, stop_usd=250.0):
    Dd, nb, _, _ = nz.days(); hard = (stop_usd - nz.FEE - 2 * nz.TICK * nz.PV) / nz.PV; out = []
    for i in range(14, len(Dd)):
        d, a = Dd[i]
        if d < nz.START or d > nz.END: continue
        pc = Dd[i - 1][1]["close_l"][nb - 1]; o, h, l, c = a["open_l"], a["high_l"], a["low_l"], a["close_l"]
        if pc != pc or abs(o[0] / pc - 1) > 0.015 or o[360] != o[360]: continue
        r = SIGS[sig](a, o[0], pc)
        if r != r or r == 0: continue
        s = mult * (1 if r > 0 else -1)
        e = o[360] + s * nz.TICK; stop = e - s * hard; mae = 0.0; px = None; xk = nb - 1
        for j in range(360, nb):
            if c[j] != c[j]: continue
            mae = max(mae, ((e - l[j]) if s > 0 else (h[j] - e)) * nz.PV)
            if (s > 0 and l[j] <= stop) or (s < 0 and h[j] >= stop):
                px = (min(stop, o[j]) if s > 0 else max(stop, o[j])) - s * nz.TICK; xk = j; break
        if px is None:
            j = nb - 1
            while c[j] != c[j]: j -= 1
            px = c[j] - s * nz.TICK; xk = j
        out.append(dict(d=d, ek=360, xk=xk, pnl=(px - e) * s * nz.PV - nz.FEE, mae=mae + nz.TICK * nz.PV, side=s))
    return pd.DataFrame(out)


def merge(a, b):
    t = pd.concat([a, b]).sort_values(["d", "ek"]).reset_index(drop=True); keep = []; last = None; busy = -1
    for r in t.itertuples():
        if r.d != last: last, busy = r.d, -1
        if r.ek <= busy: keep.append(False); continue
        keep.append(True); busy = r.xk
    return t[keep].reset_index(drop=True)


def full(t):
    o = {e: nz.stats(t, e) for e in ("IS", "HO")}
    for e in ("IS", "HO"): o[e]["roll"] = sim.eval_roll(t, e); o[e]["boot"] = sim.eval_boot(t, e)
    o["HO"]["roll_strict"] = sim.eval_roll(t, "HO", strict=True)
    return o


if __name__ == "__main__":
    nz.days(); res = {}; st = {}
    for sg in SIGS:
        for m, nm in ((1, "continuation"), (-1, "reversal")):
            t = lhh(sg, m); st[f"{sg} / {nm}"] = t; res[f"{sg} / {nm}"] = {e: nz.stats(t, e) for e in ("IS", "HO")}
    cand = [(v["IS"]["pf"], k) for k, v in res.items() if v["IS"]["net"] > 0 and v["IS"]["n"] >= 100]
    pick = max(cand)[1] if cand else None
    out = dict(variants=res, pick=pick, pick_rule="best IS PF with IS net > 0 and >= 100 IS trades")
    base = {"nolock": nz.gen(), "lock": nz.gen(lock=(100, 10))}
    # also report ALL six as add-ons (not only the IS pick) so the reader sees that the verdict does not depend on the pick
    out["addon"] = {}
    for ln, b in base.items():
        out["addon"][ln] = {"NOISE alone": full(b)}
        for k in ([pick] if pick else []) + [k for k in st if k != pick]:
            m = merge(b, st[k]); fn = "LHH_" + ln + "_" + "".join(ch if ch.isalnum() else "_" for ch in k); m.to_csv(f"{HERE}/streams/{fn}.csv", index=False)
            o = full(m); o["dropped_overlap"] = int(len(b) + len(st[k]) - len(m)); o["pick"] = bool(k == pick)
            dn, dl = sim.daily(b, "HO"), sim.daily(st[k], "HO"); both = (dn != 0) & (dl != 0)
            o["corr_ho_all_days"] = float(dn.corr(dl)); o["corr_ho_days_both"] = float(dn[both].corr(dl[both])) if both.sum() > 3 else None
            o["delta_ci_net_ho"] = sim.delta_ci(m, b, "HO")
            out["addon"][ln][k] = o
    if pick: st[pick].to_csv(HERE + "/streams/LHH_alone_pick.csv", index=False)
    out["alone"] = {k: full(v) for k, v in st.items()}
    json.dump(out, open(HERE + "/lhh.json", "w"), indent=1, default=float)
    print(pick); print({k: (v["IS"]["pf"], v["IS"]["n"], v["HO"]["pf"], v["HO"]["net"], v["HO"]["win"]) for k, v in res.items()})
