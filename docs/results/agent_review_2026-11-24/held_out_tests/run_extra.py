"""Additions requested mid-task (2026-11-24): (A) NOISE decay check + cost sensitivity, (B) VIX regime gates from FRED VIXCLS (free data).
usage: python3 run_extra.py   (writes extra_results.json, prereg_extra.json, decay_quarterly.csv, decay_rolling.csv)
VIX gate rule: the PRIOR trading day's VIX close (FRED date < trade date), so it is known before the 09:30 open. Pick-window median threshold."""
import json, time
import numpy as np, pandas as pd
import hot_lib as H
from hot_lib import stats, win, paired_boot

OUT = H.HERE
base = H.gen2(); cand = H.candace(); cand = cand[cand.d >= H.PICK0].copy()
X = {}


# ---------------------------------------------------------------- (A) decay check (descriptive, no variants)
def summ(t):
    p = t.pnl.values
    if not len(p): return dict(n=0, pf=np.nan, net=0.0, avg=np.nan, win=np.nan)
    ls = -p[p < 0].sum()
    return dict(n=int(len(p)), pf=round(float(p[p > 0].sum() / ls), 2) if ls > 0 else np.inf, net=round(float(p.sum()), 0),
                avg=round(float(p.mean()), 1), win=round(100 * float((p > 0).mean()), 1))


b = base.copy(); b["dt"] = pd.to_datetime(b.d)
q = b.groupby(b.dt.dt.to_period("Q")).apply(lambda t: pd.Series(summ(t))).reset_index().rename(columns={"dt": "quarter"})
q.to_csv(OUT + "/decay_quarterly.csv", index=False)
X["quarterly"] = q.astype({"quarter": str}).to_dict("records")
rows = []
for m in pd.period_range("2022-04", "2026-10", freq="M"):
    end = m.to_timestamp(how="end")
    r = dict(month_end=str(m))
    for L in (6, 12):
        t = b[(b.dt > end - pd.DateOffset(months=L)) & (b.dt <= end)]
        if m >= pd.Period("2021-10", "M") + L - 1:
            s = summ(t); r.update({f"pf{L}m": s["pf"], f"net{L}m": s["net"], f"n{L}m": s["n"]})
    rows.append(r)
roll = pd.DataFrame(rows); roll.to_csv(OUT + "/decay_rolling.csv", index=False)
X["rolling"] = roll.to_dict("records")
SEG = {"pick 2021-10..2023-12": ("2021-10-21", "2023-12-31"), "2024 H1": ("2024-01-01", "2024-06-30"), "2024 H2": ("2024-07-01", "2024-12-31"),
       "2025 H1": ("2025-01-01", "2025-06-30"), "2025 H2": ("2025-07-01", "2025-12-31"), "2026 (to 10-30)": ("2026-01-01", "2026-10-30")}
X["segments"] = {}
for nm, (s, e) in SEG.items():
    t = b[(b.d >= s) & (b.d <= e)]
    days = pd.bdate_range(s, e).strftime("%Y-%m-%d")
    dly = t.groupby("d").pnl.sum().reindex(days, fill_value=0.0)
    X["segments"][nm] = dict(**summ(t), sharpe=round(float(dly.mean() / dly.std() * np.sqrt(252)), 2), per_month=round(float(t.pnl.sum() / (len(days) / 21)), 0))
X["cost_sensitivity"] = {}
for cost in (2.0, 3.0, 4.0):
    bc = base.copy(); bc["pnl"] = base.pnl - (cost - 2.0)
    X["cost_sensitivity"][f"${cost:.0f}"] = {nm: {k: v for k, v in stats(bc, w).items() if k in ("n", "pf", "net", "avg", "sharpe")}
                                             for nm, w in (("pick", "pick"), ("judge", "judge"))}
    X["cost_sensitivity"][f"${cost:.0f}"]["2025H2-2026"] = summ(bc[bc.d >= "2025-07-01"])
# linear trend of quarterly $/trade (descriptive): slope per year with a rough OLS standard error
qq = q[q.n >= 10].reset_index(drop=True); xq = np.arange(len(qq)) / 4.0; yq = qq.avg.astype(float).values
A = np.vstack([np.ones_like(xq), xq]).T; coef, res, *_ = np.linalg.lstsq(A, yq, rcond=None)
se = float(np.sqrt(res[0] / (len(yq) - 2) / ((xq - xq.mean()) ** 2).sum())) if len(res) else np.nan
X["trend_avg_per_trade"] = dict(slope_per_year=round(float(coef[1]), 2), se=round(se, 2), quarters=int(len(qq)))
# random-direction context for the recent segment (is 2025H2-2026 still above luck?)
rec = []
for s in range(300):
    t = H.gen2(rnd=s); t = t[t.d >= "2025-07-01"]; rec.append(summ(t)["pf"])
X["recent_random_pf_p95"] = round(float(np.percentile(rec, 95)), 3)
X["recent_random_pf_mean"] = round(float(np.mean(rec)), 3)

# ---------------------------------------------------------------- (B) VIX gates (pre-registered; 4 more variants)
vx = pd.read_csv(OUT + "/VIXCLS.csv"); vx = vx[pd.to_numeric(vx.VIXCLS, errors="coerce").notna()]
vx["v"] = vx.VIXCLS.astype(float); vdates = vx.observation_date.values; vv = vx.v.values
def prior_vix(d):
    i = np.searchsorted(vdates, d) - 1                       # strictly before the trade date
    return float(vv[i]) if i >= 0 else np.nan
pick_days = [d for d in H.DATES if H.PICK0 <= d <= H.PICK1]
vmed = float(np.median([prior_vix(d) for d in pick_days]))
PRE = {"frozen_at": time.strftime("%Y-%m-%d %H:%M:%S"), "vix_source": "FRED VIXCLS (free), prior-day close", "pick_median_vix": vmed,
       "variants": {"V1": "NOISE only if prior VIX >= pick median", "V2": "NOISE only if prior VIX < pick median",
                    "G5": "CANDACE only if prior VIX >= pick median", "G6": "CANDACE only if prior VIX < pick median"},
       "pick_rule": "per strategy: pick trades >= 60, pick PF > base, pick net >= base; highest pick PF (else REJECT)",
       "control": "judge net above the 95th pct of 5000 random subsets of the judge trades of the same size"}
base["vix"] = [prior_vix(d) for d in base.d]; cand["vix"] = [prior_vix(d) for d in cand.d]
VAR = {"V1": (base, base.vix >= vmed), "V2": (base, base.vix < vmed), "G5": (cand, cand.vix >= vmed), "G6": (cand, cand.vix < vmed)}
PS = {k: stats(t[m], "pick") for k, (t, m) in VAR.items()}
picks = {}
for grp, ks, bt in (("noise", ("V1", "V2"), base), ("candace", ("G5", "G6"), cand)):
    bp = stats(bt, "pick"); el = [k for k in ks if PS[k]["n"] >= 60 and PS[k]["pf"] > bp["pf"] and PS[k]["net"] >= bp["net"]]
    picks[grp] = max(el, key=lambda k: PS[k]["pf"]) if el else None
PRE["pick_result"] = picks
json.dump(PRE, open(OUT + "/prereg_extra.json", "w"), indent=1)
# judge
X["vix"] = {"median": vmed, "picks": picks, "base_noise": {w: stats(base, w) for w in ("pick", "judge")},
            "base_candace": {w: stats(cand, w) for w in ("pick", "judge")}}
rnd = np.random.default_rng(13)
for k, (t, m) in VAR.items():
    tv = t[m]; X["vix"][k] = {w: stats(tv, w) for w in ("pick", "judge")}
    pj = win(t, "judge").pnl.values; n = len(win(tv, "judge"))
    nets = [rnd.choice(pj, n, replace=False).sum() for _ in range(5000)]
    X["vix"][k]["control_net_p95"] = round(float(np.percentile(nets, 95)), 0)
    X["vix"][k]["boot_judge"] = paired_boot(t, tv, "judge")
json.dump(X, open(OUT + "/extra_results.json", "w"), indent=1, default=str)
print(json.dumps({k: X[k] for k in ("segments", "cost_sensitivity", "trend_avg_per_trade", "recent_random_pf_p95", "recent_random_pf_mean", "vix")}, indent=1, default=str))
print(q.to_string())
