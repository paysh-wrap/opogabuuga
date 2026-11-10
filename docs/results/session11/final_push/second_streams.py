"""Per-market MAIN strategy (NOISE + PM fade, parameters unchanged) on MNQ / MES / MYM / M2K, 1 micro, 2021-11-01..2026-10-30.
Reuses noise_t / pm_fade from ../rebuild_main_csv.py (module constants PV / TICK / PTS swapped per market). Fee $1 RT, 1 tick slippage/side.
Stop = same % of price as MNQ's 124 pt: PTS_mkt = 124 x median(close_mkt) / median(close_MNQ), rounded to tick.
usage: second_streams.py  -> streams/second_<mkt>.csv + second_streams.json"""
import sys, json
sys.dont_write_bytecode = True
ROOT = "/home/user/opogabuuga"
sys.path[:0] = [ROOT + "/docs/results/session11", ROOT + "/docs/results/session10/five_year"]
import numpy as np, pandas as pd
import rebuild_main_csv as R
import noise_gen as NG
HERE = ROOT + "/docs/results/session11/final_push"
SPEC = {"mnq": (2.0, 0.25), "mes": (5.0, 0.25), "mym": (0.5, 1.0), "m2k": (5.0, 0.10)}
SPLIT = "2023-12-31"

def stop_pts():
    med = {m: pd.read_csv(f"{R.RAW}/{m}_5y.csv", usecols=["timestamp", "close"]).query("timestamp >= '2021-11-01'").close.median() for m in SPEC}
    out = {"mnq": 124.0}
    for m in ("mes", "mym", "m2k"):
        out[m] = round(124.0 * med[m] / med["mnq"] / SPEC[m][1]) * SPEC[m][1]
    return out, med

def stats(t):
    if not len(t): return dict(n=0)
    w = t.pnl > 0; day = t.groupby("d").pnl.sum(); cum = day.cumsum()
    return dict(n=int(len(t)), win=float(w.mean()), pf=float(t.pnl[w].sum() / -t.pnl[~w].sum()), total=float(t.pnl.sum()),
                maxdd=float((cum - cum.cummax().clip(lower=0)).min()))

if __name__ == "__main__":
    pts, med = stop_pts(); res = {}; daily = {}
    for m, (pv, tick) in SPEC.items():
        R.PV, R.TICK, R.PTS = pv, tick, pts[m]
        days, nb = NG.load_days(f"{R.RAW}/{m}_5y.csv"); assert nb == 390
        f = lambda t: t[(t.d >= R.START) & (t.d <= R.END)]
        nt = f(R.noise_t(days, pts[m])); ft = R.pm_fade(days, set(nt.d))
        t = pd.concat([nt.assign(k="noise"), ft.assign(k="fade")]).sort_values("d", kind="stable").reset_index(drop=True)
        t.to_csv(f"{HERE}/streams/second_{m}.csv", index=False)
        nd = sum(R.START <= d <= R.END for d, _ in days)
        res[m] = dict(days=nd, stop_pts=pts[m], stop_usd=pts[m] * pv + 2 * tick * pv + 1, median_px=float(med[m]), all=stats(t), h1=stats(t[t.d <= SPLIT]), h2=stats(t[t.d > SPLIT]),
                      noise=stats(t[t.k == "noise"]), fade=stats(t[t.k == "fade"]),
                      years={y: round(float(g.pnl.sum())) for y, g in t.groupby(t.d.str[:4])})
        daily[m] = t.groupby("d").pnl.sum()
    D = pd.DataFrame(daily)
    for m in ("mes", "mym", "m2k"):
        res[m]["corr_all_days"] = float(D.fillna(0)["mnq"].corr(D.fillna(0)[m]))
        both = D[["mnq", m]].dropna(); res[m]["corr_both_traded"] = float(both.mnq.corr(both[m])); res[m]["days_both"] = int(len(both))
        res[m]["same_sign_both"] = float((np.sign(both.mnq) == np.sign(both[m])).mean())
    json.dump(res, open(f"{HERE}/second_streams.json", "w"), indent=1)
    for m, r in res.items():
        print(m, f"days {r['days']} stop {r['stop_pts']}pt ${r['stop_usd']:.0f}", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r["all"].items()},
              "| H1", round(r["h1"]["total"]), f"PF {r['h1']['pf']:.2f}", "| H2", round(r["h2"]["total"]), f"PF {r['h2']['pf']:.2f}",
              "| noise", round(r["noise"]["total"]), "fade", round(r["fade"]["total"]), "| corr", round(r.get("corr_all_days", 1), 2), r["years"])
