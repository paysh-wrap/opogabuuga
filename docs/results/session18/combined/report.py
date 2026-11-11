"""Build the tables for RESULTS.md from out/results.json (python3 -I report.py) -> out/tables.md"""
import json, numpy as np, pandas as pd
HERE = "/home/user/opogabuuga/docs/results/session18/combined"
R = json.load(open(HERE + "/out/results.json")); PK = json.load(open(HERE + "/out/picks.json"))
ACCTS = ["25", "50", "100", "150"]
CONFS = ["NOISE preset C (ref)", "ICT", "SMC", "DMI", "RSI", "COMB-1 first signal wins", "COMB-2 IS-PF gated priority", "COMB-3 vote (2 agree <=30 min)", "COMB-4 first signal, <=1/day per strategy+market"]
SHORT = {"COMB-1 first signal wins": "COMB-1 first signal", "COMB-2 IS-PF gated priority": "COMB-2 IS-PF gated (SMC+ICT)", "COMB-3 vote (2 agree <=30 min)": "COMB-3 vote >=2", "COMB-4 first signal, <=1/day per strategy+market": "COMB-4 first, <=1/day/strat", "NOISE preset C (ref)": "NOISE preset C (ref)"}
def f(x, d=1, comma=True):
    if x is None or (isinstance(x, float) and (np.isnan(x))): return "-"
    if isinstance(x, float) and np.isinf(x): return "inf"
    if d == 0 and isinstance(x, float) and abs(x) > 300 and comma is None: return ">300"
    return f"{x:,.{d}f}" if comma else f"{x:.{d}f}"
def mk(s): return f"{s['n']} / {f(s['net'],0)} / {f(s['pf'],2)}" if s["n"] else "0"
def row(name, b, era, rd=None):
    s = b[era]; r = s["roll"]
    rr = "-" if rd is None else f"{f(rd[era]['pf'],2)} / {f(rd[era]['avg'],0)} / {f(rd[era]['pas'],0)}/{f(rd[era]['bust'],0)}"
    beat = "-" if rd is None else f"{sum(s['net'] > x for x in rd[era]['net_list'])}/{len(rd[era]['net_list'])}"
    return (f"| {name} | {s['n']} | {f(s['win'])} | {f(s['pf'],2)} | {f(s['payoff'],2)} | {f(s['avg'],1)} | {f(s['net'],0)} | {f(s['dd'],0)} | {f(r['pas'],0)} / {f(r['bust'],0)} ({f(r['n'],0,False)} starts) | {f(r['med'],0)} | "
            f"{mk(s['by_mkt']['MNQ'])} | {mk(s['by_mkt']['MGC'])} | {rr} | {beat} |")
HDR = ("| config | trades | win % | PF | avg win / avg loss | $/trade | net $ | max DD $ | eval PASS / BUST % (rolling) | median days to pass | MNQ: n / net $ / PF | MGC: n / net $ / PF | random-direction: PF / $/tr / PASS/BUST % | real net beats random (seeds) |\n"
       "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
out = []
for a in ACCTS:
    for era, title in (("HO", "last ~4 months (2026-07-01..2026-11-05) = JUDGE window"), ("FULL", "full 12 months (2025-11-06..2026-11-05)")):
        out += [f"\n#### Pro {a}K - {title}", HDR]
        for c in CONFS:
            b = R[a][c]["BOTH"]; rd = R[a][c].get("RAND")
            out.append(row(SHORT.get(c, c), b, era, rd))
open(HERE + "/out/tables_main.md", "w").write("\n".join(out) + "\n")
# bootstrap + seq table
B = ["| account | config | HO roll PASS/BUST % (strict) | HO roll PASS/BUST % (seq, no MAE) | 12m bootstrap PASS/BUST % (strict) | 12m bootstrap PASS/BUST % (seq) | median days (boot strict) | funded 40% consistency: largest day / net, HO | same, 12m | hedge-lock would-be vetoes (12m) | avg micros / max micros (12m) |", "|---|---|---|---|---|---|---|---|---|---|---|"]
for a in ACCTS:
    for c in CONFS:
        b = R[a][c]["BOTH"]; h = b["HO"]; fu = b["FULL"]
        B.append(f"| {a}K | {SHORT.get(c,c)} | {f(h['roll']['pas'],0)} / {f(h['roll']['bust'],0)} | {f(h['roll_seq']['pas'],0)} / {f(h['roll_seq']['bust'],0)} | {f(fu['boot']['pas'],0)} / {f(fu['boot']['bust'],0)} | {f(fu['boot_seq']['pas'],0)} / {f(fu['boot_seq']['bust'],0)} | {f(fu['boot']['med'],0)} | {f(h['cons'],0,None)}% | {f(fu['cons'],0,None)}% | {b['hedge_vetoes']} | {f(fu['avg_n'],1)} / {fu['max_n']} |")
open(HERE + "/out/tables_boot.md", "w").write("\n".join(B) + "\n")
# sensitivities
S = ["| account | combined variant | sizing / rule variant | HO trades | HO PF | HO $/tr | HO net $ | HO maxDD $ | HO PASS/BUST % | 12m trades | 12m PF | 12m net $ | 12m maxDD $ | 12m PASS/BUST % | avg micros |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for a in ACCTS:
    for conf, d in R[a]["_sens"].items():
        base = R[a][conf]["BOTH"]; d = {"base (25% MLL budget, app day rules)": base, **d}
        for nm, s in d.items():
            h, fu = s["HO"], s["FULL"]
            S.append(f"| {a}K | {SHORT.get(conf,conf)} | {nm} | {h['n']} | {f(h['pf'],2)} | {f(h['avg'],1)} | {f(h['net'],0)} | {f(h['dd'],0)} | {f(h['roll']['pas'],0)} / {f(h['roll']['bust'],0)} | {fu['n']} | {f(fu['pf'],2)} | {f(fu['net'],0)} | {f(fu['dd'],0)} | {f(fu['roll']['pas'],0)} / {f(fu['roll']['bust'],0)} | {f(fu['avg_n'],1)} |")
open(HERE + "/out/tables_sens.md", "w").write("\n".join(S) + "\n")
# market-only runs (25K and 150K)
M = ["| account | config | scope | HO n | HO win % | HO PF | HO $/tr | HO net $ | HO PASS/BUST % | 12m n | 12m PF | 12m net $ | 12m PASS/BUST % |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for a in ACCTS:
    for c in CONFS[1:]:
        for sc in ("MNQ", "MGC"):
            s = R[a][c][sc]; h, fu = s["HO"], s["FULL"]
            M.append(f"| {a}K | {SHORT.get(c,c)} | {sc} only | {h['n']} | {f(h['win'])} | {f(h['pf'],2)} | {f(h['avg'],1)} | {f(h['net'],0)} | {f(h['roll']['pas'],0)} / {f(h['roll']['bust'],0)} | {fu['n']} | {f(fu['pf'],2)} | {f(fu['net'],0)} | {f(fu['roll']['pas'],0)} / {f(fu['roll']['bust'],0)} |")
open(HERE + "/out/tables_mkt.md", "w").write("\n".join(M) + "\n")
# picks / variants
V = pd.read_csv(HERE + "/out/variants_pooled_1micro.csv")
P = ["| strategy | picked variant (best IS PF, IS n >= 25/30) | IS n / PF | HO n / PF / net $ | 12m n / PF / net $ | priority |", "|---|---|---|---|---|---|"]
for s in ("ICT", "SMC", "DMI", "RSI"):
    p = PK["picks"][s]; P.append(f"| {s} | {p['var']} | {int(p['IS_n'])} / {p['IS_pf']:.2f} | {int(p['HO_n'])} / {p['HO_pf']:.2f} / {p['HO_net']:,.0f} | {int(p['FULL_n'])} / {p['FULL_pf']:.2f} / {p['FULL_net']:,.0f} | {PK['order'].index(s)+1} |")
Vt = ["| strategy | variant | IS n | IS PF | IS net $ | HO n | HO win % | HO PF | HO net $ | 12m n | 12m PF | 12m net $ |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
for r in V.sort_values(["strat", "IS_pf"], ascending=[True, False]).itertuples():
    Vt.append(f"| {r.strat} | {r.var} | {r.IS_n} | {r.IS_pf:.2f} | {r.IS_net:,.0f} | {r.HO_n} | {r.HO_win:.1f} | {r.HO_pf:.2f} | {r.HO_net:,.0f} | {r.FULL_n} | {r.FULL_pf:.2f} | {r.FULL_net:,.0f} |")
open(HERE + "/out/tables_picks.md", "w").write("\n".join(P) + "\n\n" + "\n".join(Vt) + "\n")
# subsets
SB = pd.read_csv(HERE + "/out/subsets.csv"); T = []
for a in (25, 150):
    T += [f"\n#### Pro {a}K sizing - every subset of the four picked strategies, first-signal-wins (exploratory)", "| subset | IS n | IS PF | IS net $ | HO n | HO win % | HO PF | HO net $ | HO PASS/BUST % | 12m n | 12m PF | 12m net $ | 12m PASS/BUST % |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in SB[SB.acct == a].itertuples():
        T.append(f"| {r.subset} | {r.IS_n} | {r.IS_pf:.2f} | {r.IS_net:,.0f} | {r.HO_n} | {r.HO_win:.1f} | {r.HO_pf:.2f} | {r.HO_net:,.0f} | {r.HO_pass:.0f} / {r.HO_bust:.0f} | {r.FULL_n} | {r.FULL_pf:.2f} | {r.FULL_net:,.0f} | {r.FULL_pass:.0f} / {r.FULL_bust:.0f} |")
open(HERE + "/out/tables_subsets.md", "w").write("\n".join(T) + "\n")
print(open(HERE + "/out/tables_main.md").read())
