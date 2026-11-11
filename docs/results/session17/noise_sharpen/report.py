"""Builds RESULTS_tables.md (all numeric tables) from study.json / stage2.json / randbench.json / lhh.json / baseline_check.json. RESULTS.md = text + these tables."""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, pandas as pd
import nz, sim

S = json.load(open(HERE + "/study.json"))["variants"]; S2 = json.load(open(HERE + "/stage2.json")); RB = json.load(open(HERE + "/randbench.json"))
LH = json.load(open(HERE + "/lhh.json")); BC = json.load(open(HERE + "/baseline_check.json"))
ALL = dict(S); ALL.update(S2["combos"])
_st = {}


def stream(n):
    if n not in _st: _st[n] = pd.read_csv(f"{HERE}/streams/{ALL[n]['file']}.csv", dtype={"d": str})
    return _st[n]


def base_of(n):
    if n.endswith("[lock]") or n.startswith("COMBO"): return "BASE [lock]"
    return "BASE [nolock]"


def yr_pf(t):
    o = {}
    for y, g in t.groupby(t.d.str[:4]):
        w = g.pnl > 0; gl = -g.pnl[~w].sum(); o[y] = g.pnl[w].sum() / gl if gl > 0 else 9.99
    return o


def yrs_better(n):
    b = yr_pf(stream(base_of(n))); v = yr_pf(stream(n)); ys = [y for y in b if y in v]
    return sum(v[y] >= b[y] for y in ys), len(ys)


def verdict(n):
    """machine check vs own base (held-out): all five must hold + IS PF not worse"""
    r, b = ALL[n], ALL[base_of(n)]; h, hb = r["HO"], b["HO"]
    ok = (h["avg"] > hb["avg"] and h["roll"]["pass_"] >= hb["roll"]["pass_"] and h["roll"]["bust"] <= hb["roll"]["bust"] and h["boot"]["pass_"] >= hb["boot"]["pass_"]
          and h["boot"]["bust"] <= hb["boot"]["bust"] and r["IS"]["pf"] >= b["IS"]["pf"])
    return ok


HDR = "| variant | HO trades | win % | $/trade | net $ | max DD $ | PF | roll PASS / BUST / open % | days to pass (med) | boot PASS / BUST % (med d) | strict PASS / BUST % | dNet vs base [95% CI] | IS PF (net) | yrs PF>=base |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"


def row(n, mark=""):
    r = ALL[n]; h = r["HO"]; i = r["IS"]; b = base_of(n)
    d = sim.delta_ci(stream(n), stream(b), "HO") if n != b else (0.0, 0.0, 0.0)
    yb = yrs_better(n)
    ci = "-" if n == b else f"{d[0]:+,.0f} [{d[1]:+,.0f}, {d[2]:+,.0f}]"
    return (f"| {mark}{n} | {h['n']} | {h['win']:.1f} | {h['avg']:.1f} | {h['net']:,.0f} | {h['dd']:,.0f} | {h['pf']:.2f} | {h['roll']['pass_']:.1f} / {h['roll']['bust']:.1f} / {h['roll']['open_']:.1f} | "
            f"{h['roll']['med']:.0f} | {h['boot']['pass_']:.1f} / {h['boot']['bust']:.1f} ({h['boot']['med']:.0f}) | {h['roll_strict']['pass_']:.1f} / {h['roll_strict']['bust']:.1f} | {ci} | {i['pf']:.2f} ({i['net']:,.0f}) | {yb[0]}/{yb[1]} |\n")


def table(names, sel=()):
    return HDR + "".join(row(n, "**IS-pick** " if n in sel else "") for n in names)


sel = set(S2["selected"]["lock"].values()) | set(S2["selected"]["nolock"].values())
out = []
# ---- baselines
ib = BC
out.append("### T1 baseline reproduction (1 micro)\n| run | era | trades | win % | $/trade | PF | max DD $ | session-9 record |\n|---|---|---|---|---|---|---|---|\n")
rec = {"IS": "727 / 44.3% / +15.28 / 1.32 / -1,466", "HO": "440 / 45.0% / +25.81 / 1.33 / -2,214"}
for lab, key in (("session-9 original (1% stop)", "session9_1pct"), ("app default ($250 stop, engine/noise.py + NoiseCfg)", "app_default_250"), ("preset C ($250 stop + lock 100->+10)", "preset_C_250_lock")):
    for e in ("IS", "HO"):
        s = ib[key][e]
        out.append(f"| {lab} | {e} | {s['n']} | {s['win']:.1f} | {s['avg']:.2f} | {s['pf']:.2f} | {s['dd']:,.0f} | {rec[e] if key=='session9_1pct' else ''} |\n")
out.append(f"\nTrade-for-trade check vs `tools/noise_area.py` (independent session-9 code, same CSV): identical = **{ib['session9_1pct']['identical_to_tools_noise_area']}** ({ib['session9_1pct']['n_mine']} trades).\n"
           f"Trade-for-trade check vs committed session-15 stream `out/streams/N1_MNQ.csv` (lock 100/10, window {ib['vs_session15_N1']['window'][0]}..{ib['vs_session15_N1']['window'][1]}): identical = **{ib['vs_session15_N1']['identical']}** "
           f"({ib['vs_session15_N1']['n_mine']} trades, net ${ib['vs_session15_N1']['net_mine']:,.0f}).\n\n")
out.append("### T1b per-year profit factor (all trades of the year, 1 micro)\n| stream | " + " | ".join(str(y) for y in range(2019, 2027)) + " |\n|---|" + "---|" * 8 + "\n")
for n in ("session-9 original (1% stop) [nolock]", "BASE [nolock]", "BASE [lock]"):
    y = yr_pf(stream(n)); out.append(f"| {n} | " + " | ".join(f"{y.get(str(k), float('nan')):.2f}" for k in range(2019, 2027)) + " |\n")
out.append("\n")
# ---- N10-12
nn = ["BASE [nolock]", "N10 skip low-vol tercile [nolock]", "N11 skip Monday [nolock]", "N12 skip Friday [nolock]", "N10+N11 [nolock]", "N11+N12 (Tue-Thu only) [nolock]",
      "BASE [lock]", "N10 skip low-vol tercile [lock]", "N11 skip Monday [lock]", "N12 skip Friday [lock]", "N10+N11 [lock]", "N11+N12 (Tue-Thu only) [lock]"]
out.append("### T2 N10 / N11 / N12 day filters (held-out)\n" + table(nn[:6], sel) + "\n" + table(nn[6:], sel) + "\n")
# ---- VWAP
vn = ["BASE [nolock]", "VWAP side filter [nolock]", "VWAP side+slope filter [nolock]", "BASE [lock]", "VWAP side filter [lock]", "VWAP side+slope filter [lock]"]
out.append("### T3 VWAP entry filter (long only above session VWAP, short only below; slope = VWAP also rising/falling over 60 min)\n" + table(vn[:3], sel) + "\n" + table(vn[3:], sel) + "\n")
# ---- locks
ln = ["BASE [nolock]", "session-9 original (1% stop) [nolock]"] + [n for n in S if S[n]["fam"] == "lock"] + [n for n in S if S[n]["fam"] == "tlock"]
out.append("### T4 profit-lock variants ($250 stop everywhere; 'lock T->+L' = once +T points in favour the stop moves to entry+L points; a lock exit ends NOISE for the day; trail-lock = stop trails best price minus the give-back; compared with plain BASE [nolock]; the shipped preset C is `lock 100->+10` = BASE [lock])\n" + table(ln, sel) + "\n")
# ---- extras
ex = ["BASE [lock]"] + [n for n in S if n.endswith("[lock]") and S[n]["fam"] in ("hours", "norev", "width", "addon-1530")]
out.append("### T5 other filters from the earlier unfinished scripts (applied on the preset-C base)\n" + table(ex, sel) + "\n")
ex2 = ["BASE [nolock]"] + [n for n in S if n.endswith("[nolock]") and S[n]["fam"] in ("hours", "norev", "width", "addon-1530")]
out.append("### T5b the same on the plain base (no lock)\n" + table(ex2, sel) + "\n")
# ---- selection + combos
out.append("### T6 IS-only selection (rule fixed before looking at held-out) and combinations\nSelected per family on the plain base: " + json.dumps(S2["selected"]["nolock"]) + "\n\nSelected per family on the preset-C base: " + json.dumps(S2["selected"]["lock"]) + "\n\nIS ranking of filter families on the preset-C base (IS edge ratio): " + ", ".join(f"{n.replace(' [lock]','')} ({r:.2f})" for f, n, r in S2["ranked"]) + "\n\n")
out.append(table(["BASE [lock]"] + list(S2["combos"]), sel) + "\n")
# ---- random bench
def pc(v, x): return 100 * float((np.array(v) < x).mean())
out.append("### T7 random-direction benchmark (200 seeds per base; same timing, exits, costs; direction = coin)\n| base | era | metric | random mean | random 5th-95th pct | random best of 200 | real strategy | real beats % of seeds |\n|---|---|---|---|---|---|---|---|\n")
for l in ("nolock", "lock"):
    xs = list(RB[l].values()); b = S[f"BASE [{l}]"]
    for e in ("IS", "HO"):
        for k, lab, f in (("avg", "$/trade", "{:.1f}"), ("net", "net $", "{:,.0f}"), ("pf", "PF", "{:.2f}"), ("win", "win %", "{:.1f}"), ("n", "trades", "{:.0f}")):
            v = np.array([x[e][k] for x in xs])
            out.append(f"| {l} | {e} | {lab} | {f.format(v.mean())} | {f.format(np.percentile(v,5))} .. {f.format(np.percentile(v,95))} | {f.format(v.max())} | {f.format(b[e][k])} | {pc(v, b[e][k]):.1f} |\n")
        p = np.array([x[e]["roll"]["pass_"] for x in xs]); bu = np.array([x[e]["roll"]["bust"] for x in xs])
        out.append(f"| {l} | {e} | Pro 25K roll PASS % | {p.mean():.1f} | {np.percentile(p,5):.1f} .. {np.percentile(p,95):.1f} | {p.max():.1f} | {b[e]['roll']['pass_']:.1f} | {pc(p, b[e]['roll']['pass_']):.1f} |\n")
        out.append(f"| {l} | {e} | Pro 25K roll BUST % | {bu.mean():.1f} | {np.percentile(bu,5):.1f} .. {np.percentile(bu,95):.1f} | {bu.min():.1f} (lowest) | {b[e]['roll']['bust']:.1f} | {100*float((bu>b[e]['roll']['bust']).mean()):.1f} (seeds with MORE busts) |\n")
out.append("\n")
# ---- LHH
out.append("### T8 last-half-hour momentum (15:30 -> 16:00, $250 stop, 1 micro): the six candidate signals alone\n| signal / mode | IS trades | IS win % | IS PF | IS net $ | HO trades | HO win % | HO PF | HO net $ |\n|---|---|---|---|---|---|---|---|---|\n")
for k, v in LH["variants"].items():
    i, h = v["IS"], v["HO"]
    out.append(f"| {'**IS-pick** ' if k == LH['pick'] else ''}{k} | {i['n']} | {i['win']:.1f} | {i['pf']:.2f} | {i['net']:,.0f} | {h['n']} | {h['win']:.1f} | {h['pf']:.2f} | {h['net']:,.0f} |\n")
out.append("\n### T9 LHH as an add-on to NOISE (one position at a time; LHH trade dropped if NOISE is still open at 15:30)\n" + HDR.replace("| variant |", "| stream |").replace("| yrs PF>=base |", "| corr(day P&L) HO |").replace("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"))
for l in ("nolock", "lock"):
    A = LH["addon"][l]; bnm = f"BASE [{l}]"
    for k, v in A.items():
        h, i = v["HO"], v["IS"]; hb = ALL[bnm]["HO"]
        if k == "NOISE alone": ci = "-"; cor = "-"; nm = f"NOISE alone [{l}]"
        else:
            d = v["delta_ci_net_ho"]; ci = f"{d[0]:+,.0f} [{d[1]:+,.0f}, {d[2]:+,.0f}]"; cor = f"{v['corr_ho_days_both']:.2f}" if v["corr_ho_days_both"] is not None else "-"
            nm = f"{'**IS-pick** ' if v['pick'] else ''}NOISE[{l}] + LHH {k}"
        out.append(f"| {nm} | {h['n']} | {h['win']:.1f} | {h['avg']:.1f} | {h['net']:,.0f} | {h['dd']:,.0f} | {h['pf']:.2f} | {h['roll']['pass_']:.1f} / {h['roll']['bust']:.1f} / {h['roll']['open_']:.1f} | {h['roll']['med']:.0f} | {h['boot']['pass_']:.1f} / {h['boot']['bust']:.1f} ({h['boot']['med']:.0f}) | {h['roll_strict']['pass_']:.1f} / {h['roll_strict']['bust']:.1f} | {ci} | {i['pf']:.2f} ({i['net']:,.0f}) | {cor} |\n")
# ---- machine verdict
out.append("\n### T10 machine check: which variants beat their own base on ALL held-out tests?\n(HO $/trade up, roll PASS >= base, roll BUST <= base, boot PASS >= base, boot BUST <= base, and IS PF >= base IS PF.)\n\n")
okn = [n for n in ALL if "BASE" not in n and not n.startswith("session-9") and verdict(n)]
out.append(f"{len(okn)} of {len([n for n in ALL if 'BASE' not in n and not n.startswith('session-9')])} variants pass: \n\n" + table(okn, sel) + "\n")

MASTER = ["session-9 original (1% stop) [nolock]", "BASE [nolock]", "BASE [lock]", "N11 skip Monday [lock]", "N10 skip low-vol tercile [lock]", "N12 skip Friday [lock]",
          "VWAP side filter [lock]", "min sigma >= IS p20 (0.29%) [lock]", "lock 75->+10", "lock 200->+10", "trail-lock +100 give back 100",
          "no entry 11:00 [lock]", "extra check 15:30 (band entry) [lock]"] + list(S2["combos"])
m = ["### T0 master table, held-out 2024-01..2026-11 (1 micro; every row also in the detail tables). Base of a [lock] row = BASE [lock] (= preset C); base of a [nolock] row = BASE [nolock] (= app default)\n", table(MASTER, sel)]
rb = {l: list(RB[l].values()) for l in RB}
for l in ("nolock", "lock"):
    xs = rb[l]; f = lambda k: np.mean([x["HO"][k] for x in xs])
    m.append(f"| random direction, same exits [{l}] (mean of 200 seeds) | {f('n'):.0f} | {f('win'):.1f} | {f('avg'):.1f} | {f('net'):,.0f} | {f('dd'):,.0f} | {f('pf'):.2f} | {np.mean([x['HO']['roll']['pass_'] for x in xs]):.1f} / {np.mean([x['HO']['roll']['bust'] for x in xs]):.1f} / {np.mean([x['HO']['roll']['open_'] for x in xs]):.1f} | {np.nanmedian([x['HO']['roll']['med'] for x in xs]):.0f} | - | - | - | - | - |\n")
out.insert(0, "".join(m) + "\n")

# ---- paired bootstrap
PD = json.load(open(HERE + "/paired.json"))
out.append("\n### T13 paired block-bootstrap of the Pro 25K eval outcome difference (variant minus its base, held-out days resampled in 10-session blocks, 400 resamples)\n| variant (vs its base) | dPASS % [95% CI] | P(PASS better) | dBUST % [95% CI] | P(BUST lower) |\n|---|---|---|---|---|\n")
for n, r in PD.items():
    out.append(f"| {n} | {r['dpass']:+.1f} [{r['dpass_lo']:+.1f}, {r['dpass_hi']:+.1f}] | {r['p_pass_better']:.2f} | {r['dbust']:+.1f} [{r['dbust_lo']:+.1f}, {r['dbust_hi']:+.1f}] | {r['p_bust_lower']:.2f} |\n")
open(HERE + "/RESULTS_tables.md", "w").write("".join(out))
print(len(okn), okn)
