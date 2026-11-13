"""Session 22: ORDER FLOW (D101 AR Model + D108 Casper, shipped config) on 5y MNQ (main) / MES (check) with a SIMULATED footprint.
PRE-REGISTERED (written before J was looked at):
  IS 2021-10-01..2025-11-05 picks; J 2025-11-06..2026-10-30 judges the single pick once. Path filter OFF in every grid row (no Asia data);
  the shipped path-ON config is reported as its own row (0 trades). Grid k{1.0,1.5} x exit{2R,trail5} x location{ON,OFF} x casper{ON,OFF} = 16 rows.
  Eligible: IS n>=150 and IS PF>1.05; score = IS $/trade * sqrt(IS n); none eligible -> best score, flagged.
  Edge verdict: J PF>=1.15 AND J net>0 AND pick beats >=27/30 random-side seeds on J AND eligible pick.
  MES: the MNQ pick unchanged (MNQ-IS thresholds). Accounts: session-21 9-plan bootstrap vs the session-20 NOISE stream.
Usage: .venv/bin/python run.py   (about 5 minutes)"""
import sys, json, os, math, time
sys.path[:0] = ["/home/user/opogabuuga/docs/results/session15", "/home/user/opogabuuga/docs/results/session22/orderflow_footprint"]
import numpy as np, pandas as pd, yaml
from types import SimpleNamespace as NS
from decimal import Decimal as Dc
import of, ob
import lib
OUT = os.path.dirname(os.path.abspath(__file__))
IS_END, J_START = "2025-11-05", "2025-11-06"
t0 = time.time()
D, E = of.load()
mnq = of.Mkt(D, "MNQ", IS_END); Z = mnq.build()
Ed = [(d, E[d]) for d, _ in D if d in E]
mes = of.Mkt(Ed, "MES", IS_END); mes.build(Z)          # MES uses the MNQ-IS thresholds (scale-free ratios): no re-pick, no re-fit
print("built", round(time.time() - t0), "s; thresholds", Z, flush=True)
res = dict(Z=Z, imputed=dict(MNQ=mnq.imputed / mnq.vol.size, MES=mes.imputed / mes.vol.size), is_end=IS_END, j_start=J_START)

# ------------------------------------------------------------- validation of the vectorised footprint against the app's own code
rng = np.random.default_rng(1); okp = okd = 0; NV = 200
for _ in range(NV):
    di = int(rng.integers(1, mnq.nd)); m = int(rng.integers(1, of.NC))
    ag = mnq.app_ladder(di, m)
    poc = max(ag.items(), key=lambda kv: (kv[1][0] + kv[1][1], -kv[0]))[0]
    okp += abs(float(poc) - (mnq.poc5[di, m] - mnq.row / 2)) < 1e-9
    d = sum(a - b for b, a in ag.values()); okd += abs(float(d) - mnq.D5[di, m] * 1000) < 1e-3 * max(1, abs(mnq.D5[di, m] * 1000)) + 5
res["validation"] = dict(n=NV, poc_match=int(okp), delta_match=int(okd))
print("validation vs app footprint:", res["validation"], flush=True)

# ------------------------------------------------------------- grid (path OFF)
cands = {k: mnq.candidates(k) for k in (1.0, 1.5)}
cache = {}
def run_cfg(mk, tag, k, ex, loc, cas, locdef="close", cd=None):
    mk.locdef = locdef
    mode = "2R" if ex == "2R" else "trail"
    rows = mk.simulate(k, loc, cas, mode, cand=cd if cd is not None else cands[k])
    mk.locdef = "close"
    return rows
grid = []
for k in (1.0, 1.5):
    for ex in ("2R", "trail5"):
        for loc in (True, False):
            for cas in (True, False):
                rows = run_cfg(mnq, "MNQ", k, ex, loc, cas); cache[(k, ex, loc, cas, "close")] = rows
                grid.append(dict(k=k, ex=ex, loc=loc, cas=cas, locdef="close", IS=ob.stats(rows, None, IS_END)))
for g in grid:
    g["elig"] = bool(g["IS"]["n"] >= 150 and g["IS"]["pf"] > 1.05); g["score"] = g["IS"]["per"] * math.sqrt(g["IS"]["n"]) if g["IS"]["n"] else -1e9
el = [g for g in grid if g["elig"]]; fallback = not el
pick = max(el if el else grid, key=lambda g: (g["score"], g["IS"]["pf"]))   # literal pre-registered rule
# DEVIATION (decided after the IS table, before J was computed): with no eligible row the literal rule can select a row with a handful of
# IS trades (location ON). A second pick is therefore judged as well: best score among rows with IS n >= 150 (all location OFF).
big = [g for g in grid if g["IS"]["n"] >= 150]
pick2 = max(big, key=lambda g: (g["score"], g["IS"]["pf"])) if big else pick
picks = {"literal": pick}
if pick2 is not pick: picks["n150"] = pick2
print("PICK literal (IS only):", {k: pick[k] for k in ("k", "ex", "loc", "cas", "elig", "score")}, pick["IS"]["n"], "| n>=150 pick:", {k: pick2[k] for k in ("k", "ex", "loc", "cas", "score")}, "eligible rows:", len(el), flush=True)
# ---- only now J numbers are computed for every row (shown for completeness, labelled not-picked)
for g in grid:
    g["J"] = ob.stats(cache[(g["k"], g["ex"], g["loc"], g["cas"], "close")], J_START, None)
# diagnostic rows: location measured at the absorption extreme (touch-zone) instead of the candle close; never eligible for the pick
diag = []
for k in (1.0, 1.5):
    for ex in ("2R", "trail5"):
        for cas in (True, False):
            rows = run_cfg(mnq, "MNQ", k, ex, True, cas, "extreme"); cache[(k, ex, True, cas, "extreme")] = rows
            diag.append(dict(k=k, ex=ex, loc=True, cas=cas, locdef="extreme", IS=ob.stats(rows, None, IS_END), J=ob.stats(rows, J_START, None)))
res["grid"] = grid; res["diag"] = diag; res["fallback"] = fallback
# ---- shipped config as-is (path filter ON, no Asia fields -> OF_PATH_UNKNOWN)
cnt = {}
asis = mnq.simulate(1.0, True, True, "2R", path=True, cand=cands[1.0], count=cnt)
res["as_is"] = dict(trades=len(asis), first_layer_counts=cnt, note="location ON, casper ON, path ON, k=1.0, 2R")
print("as-is shipped:", res["as_is"], flush=True)

# ------------------------------------------------------------- judge each pick on J (once)
def judge(name, pk):
    mode = "2R" if pk["ex"] == "2R" else "trail"
    rows = cache[(pk["k"], pk["ex"], pk["loc"], pk["cas"], "close")]
    pd.DataFrame(rows).drop(columns=["di"]).to_csv(f"{OUT}/streams_pick_MNQ{'' if name == 'literal' and len(picks) == 1 else '_' + name}.csv", index=False)
    o = dict(k=pk["k"], ex=pk["ex"], loc=pk["loc"], cas=pk["cas"], eligible=not fallback, IS=pk["IS"], J=pk["J"],
             per_year={y: ob.stats(rows, f"{y}-01-01", f"{y}-12-31") for y in range(2021, 2027)})
    Jr = [r for r in rows if r["d"] >= J_START]; Ir = [r for r in rows if r["d"] <= IS_END]
    rsJ = np.array([mnq.random_side(Jr, mode, s).mean() if Jr else 0.0 for s in range(30)])
    rsI = np.array([mnq.random_side(Ir, mode, s).mean() if Ir else 0.0 for s in range(30)])
    pj = pk["J"]["per"]
    o["random"] = dict(seeds_J=rsJ.tolist(), mean_J=float(rsJ.mean()), beats_J=int((pj > rsJ).sum()), pick_J_per=pj,
                       mean_IS=float(rsI.mean()), beats_IS=int((pk["IS"]["per"] > rsI).sum()), pick_IS_per=pk["IS"]["per"])
    o["edge"] = bool(pk["J"]["n"] > 0 and pk["J"]["pf"] >= 1.15 and pk["J"]["net"] > 0 and o["random"]["beats_J"] >= 27 and not fallback)
    mrows = run_cfg(mes, "MES", pk["k"], pk["ex"], pk["loc"], pk["cas"], cd=mes.candidates(pk["k"]))   # same config, unchanged
    pd.DataFrame(mrows).drop(columns=["di"]).to_csv(f"{OUT}/streams_pick_MES{'' if name == 'literal' and len(picks) == 1 else '_' + name}.csv", index=False)
    o["mes"] = dict(IS=ob.stats(mrows, None, IS_END), J=ob.stats(mrows, J_START, None), per_year={y: ob.stats(mrows, f"{y}-01-01", f"{y}-12-31") for y in range(2021, 2027)})
    snaps = []
    for r in sorted(Jr, key=lambda r: (r["d"], r["ek"]))[-3:]:
        di, m = r["di"], r["m"]; ag = mnq.app_ladder(di, m)
        poc = max(ag.items(), key=lambda kv: (kv[1][0] + kv[1][1], -kv[0]))[0]
        lad = [dict(price=float(p), bid=float(b), ask=float(a), delta=float(a - b), poc=(p == poc)) for p, (b, a) in sorted(ag.items(), reverse=True)]
        f, info = mnq.fields(di, m, r["side"]); pv_ = mnq.prior[di]
        hm = lambda k: f"{9 + (30 + k) // 60:02d}:{(30 + k) % 60:02d}"
        snaps.append(dict(date=r["d"], side="LONG" if r["side"] > 0 else "SHORT", kind="ABSORPTION" if r["kind"] == 1 else "DELTA FLIP",
                          confirm_candle=f"{hm(5 * m)}-{hm(5 * m + 5)} ET", O=float(mnq.O5[di, m]), H=float(mnq.H5[di, m]), L=float(mnq.L5[di, m]), C=float(mnq.C5[di, m]),
                          candle_delta=float(mnq.D5[di, m] * 1000), cvd_at_entry=float(mnq.cvd[di, r["ek"] - 1] * 1000), est_poc=float(mnq.poc5[di, m]),
                          stacked_buy=int(mnq.stk_buy[di, m]), stacked_sell=int(mnq.stk_sell[di, m]), env={1: "EXPANSION", 2: "ROTATION"}.get(int(mnq.env[di, m])),
                          fib=str(f.fib), value_side=f.value_side, prior_day_val_vah_poc=[float(x) for x in pv_] if pv_ else None,
                          entry_bar=hm(r["ek"]), limit=r["lim"], fill=r["e"], stop=r["stop"], target=r["tp"] if mode == "2R" else None,
                          exit_bar=hm(r["xk"]), pnl=r["pnl"], ladder=lad))
    o["snapshots"] = snaps
    return o, rows
res["picks"] = {}; prow = {}
for name, pk in picks.items():
    res["picks"][name], prow[name] = judge(name, pk)
    o = res["picks"][name]
    print(name, "IS", o["IS"], "\n   J", o["J"], "\n   beats", o["random"]["beats_J"], "edge", o["edge"], "\n   MES", o["mes"]["IS"], o["mes"]["J"], flush=True)

# ------------------------------------------------------------- accounts (session-21 bootstrap, same engine / NOISE stream)
PL = ["pro_25k", "pro_50k", "pro_100k", "pro_150k", "flex_25k", "flex_50k", "flex_100k", "flex_150k", "daily_25k"]
import subprocess
def plan(n, rev=None):
    txt = subprocess.run(["git", "-C", "/home/user/opogabuuga", "show", f"{rev}:config/rules/lucid_{n}.yaml"], capture_output=True, text=True, check=True).stdout if rev \
        else open(f"/home/user/opogabuuga/config/rules/lucid_{n}.yaml").read()
    y = yaml.safe_load(txt); e = y["eval"]; s = y["account_size"]
    q = next((r["contracts"] for r in y.get("strategy", {}).get("size_table", []) if r["account_size"] == s), 1)
    fl = lambda x: None if x is None else float(x)
    return NS(start=float(s), e=NS(target=fl(e["profit_target"]), mll=fl(e["max_loss_limit"]), lt=fl(e["lock_trigger"]), ll=fl(e["lock_level"]),
              dll=fl(e["daily_loss_limit"]), cons=fl(e["consistency_max_day_pct"]), mpd=int(e["min_profitable_days"]))), q
noise = pd.read_csv("/home/user/opogabuuga/docs/results/session20/strategy_review/streams_BASE.csv")
dates = mnq.dates
def tab_from(rows_or_df, era):
    ds = [d for d in dates if (d <= IS_END if era == "IS" else d >= J_START)]
    by = {}
    it = rows_or_df.to_dict("records") if hasattr(rows_or_df, "to_dict") else rows_or_df
    for r in sorted(it, key=lambda r: (r["d"], r["ek"])): by.setdefault(r["d"], []).append((r["pnl"], r["mae"], r["risk"]))
    return [by.get(d, []) for d in ds]
def boot(tab, R, q, seed=7, paths=600, H=400):
    rg = np.random.default_rng(seed); n = len(tab); outs = []; days = []
    for _ in range(paths):
        seq = []
        while len(seq) < H:
            s0 = int(rg.integers(0, n - 10 + 1)); seq += tab[s0:s0 + 10]
        o, d = lib.eval_run(seq[:H], R, {"q": q}, H); outs.append(o)
        if o == "PASS": days.append(d)
    return dict(pass_=100 * outs.count("PASS") / paths, bust=100 * outs.count("BUST") / paths, open_=100 * outs.count("OPEN") / paths,
                med=float(np.median(days)) if days else None)
streams = {nm.upper(): r for nm, r in prow.items()}; streams["NOISE"] = noise
S21 = "87ef163"   # commit of session 21: the Pro plan YAMLs were changed afterwards (D138: eval consistency 40%, DLL 600)
tabs = {(nm, era): tab_from(st, era) for nm, st in streams.items() for era in ("IS", "J")}
res["accounts"] = {}; res["accounts_current_pro"] = {}
for n in PL:
    R, q = plan(n, S21); res["accounts"][n] = dict(q=q)
    for (nm, era), tb in tabs.items(): res["accounts"][n][f"{nm}_{era}"] = boot(tb, R, q)
    print(n, {k: (round(v["pass_"]), round(v["bust"])) for k, v in res["accounts"][n].items() if k != "q"}, flush=True)
    if n.startswith("pro_"):   # same bootstrap with TODAY's Pro YAMLs (D138)
        R, q = plan(n); res["accounts_current_pro"][n] = dict(q=q)
        for (nm, era), tb in tabs.items(): res["accounts_current_pro"][n][f"{nm}_{era}"] = boot(tb, R, q)
res["stream_stats"] = dict(NOISE_IS=ob.stats(noise.to_dict("records"), None, IS_END), NOISE_J=ob.stats(noise.to_dict("records"), J_START, None))
s21 = json.load(open("/home/user/opogabuuga/docs/results/session21/orderblock_footprint/results.json"))["accounts"]
res["noise_matches_s21"] = all(abs(res["accounts"][n][f"NOISE_{e}"][x] - s21[n][f"NOISE_{e}"][x]) < 1e-9 for n in PL for e in ("IS", "J") for x in ("pass_", "bust"))
print("NOISE matches session 21 (s21-era plan YAMLs):", res["noise_matches_s21"])
res["runtime_s"] = round(time.time() - t0)
json.dump(res, open(f"{OUT}/results.json", "w"), indent=1, default=float)
print("done", res["runtime_s"], "s")
