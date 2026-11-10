"""kelly_tables.py - kelly_results.json -> kelly_sizing.md body (tables + mechanical verdicts). usage: python3 kelly_tables.py"""
import json, sys
R = json.load(open("kelly_results.json"))
def get(kind, plan, stream, kelly): return next(r for r in R if r["kind"] == kind and r["plan"] == plan and r["stream"] == stream and (r["kelly"] or None) == (list(kelly) if kelly else None))
PL = ["25K", "50K", "100K", "150K"]; L = []; W = L.append
NB, NI, NP = 3.0, 10.0, 3.0
def fe(r, e): x = r[e]; return f"{x['pass_']:.0f} / {x['frozen']:.0f} / {x['bust']:.0f} / {x['med']:.0f}"
def ff(r, e): x = r[e]; return f"{x['bust']:.0f}% / ${x['inc']:.0f} / ${x['surv']:.0f} / ${x['med']:.0f}"
W("## A. Profit lock (NOISE +100 pts -> stop to +10, no re-entry) vs baseline, live size tables\n")
W("EVAL: pass / frozen / bust % / median sessions to pass. Lock replayed intraday inside the engine (no day-level approximation).\n")
W("| plan | stream | all starts | 2021-23 | 2024-26 |\n|---|---|---|---|---|")
for p in PL:
    for s in ("base", "lock"): r = get("E", p, s, None); W(f"| {p} | {s} | {fe(r,'all')} | {fe(r,'e1')} | {fe(r,'e2')} |")
W("\nFUNDED year 1 (260 sessions): dead % / mean income per 2 wk / survivor income per 2 wk / median per 2 wk.\n")
W("| plan | stream | all starts | 2021-23 | 2024-26 |\n|---|---|---|---|---|")
for p in PL:
    for s in ("base", "lock"): r = get("F", p, s, None); W(f"| {p} | {s} | {ff(r,'all')} | {ff(r,'e1')} | {ff(r,'e2')} |")
def fverdict(c, l):
    v = []
    for e in ("e1", "e2"):
        db = c[e]["bust"] - l[e]["bust"]; di = c[e]["inc"] - l[e]["inc"]
        v.append("better" if (di > NI and db <= NB) or (db < -NB and di >= -NI) else ("worse" if (db > NB or di < -NI) else "same"))
    return "PASS" if v == ["better", "better"] else ("FAIL (" + "/".join(v) + ")")
def everdict(c, l):
    v = []
    for e in ("e1", "e2"):
        dp = c[e]["pass_"] - l[e]["pass_"]; dm = c[e]["med"] - l[e]["med"]
        v.append("better" if (dp > NP and dm <= 3) or (dp >= -NP and dm < -3) else ("worse" if (dp < -NP or (dm > 3 and dp <= NP)) else "same"))
    return "PASS" if v == ["better", "better"] else ("FAIL (" + "/".join(v) + ")")
KS = (0.4, 0.6, 0.8, 1.0, 1.3)
for s in ("base", "lock"):
    W(f"\n## B. Cushion-proportional sizing, FUNDED - stream = {s}\n")
    W("n = clamp(floor(k x cushion / 1000), 1, cap). Cells: dead % / mean per 2 wk / survivor per 2 wk / median per 2 wk; avg q = mean micros per session. PICK = best 2021-23 mean income among rules whose 2021-23 dead % is not above live (else lowest dead %).\n")
    for p in PL[1:]:
        live = get("F", p, s, None); cap0 = {"50K": 2, "100K": 2, "150K": 3}[p]
        W(f"\n**{p}** (live table size {cap0})\n\n| rule | avg q | 2021-23 | 2024-26 | vs live |\n|---|---|---|---|---|")
        W(f"| LIVE table | {live['all']['q']:.2f} | {ff(live,'e1')} | {ff(live,'e2')} | - |")
        f1 = get("F", p, s, (0, 1)); W(f"| fixed 1 micro | 1.00 | {ff(f1,'e1')} | {ff(f1,'e2')} | {fverdict(f1, live)} |")
        cand = [get("F", p, s, (k, cap0 + d)) for k in KS for d in (0, 1, 2)]
        ok = [c for c in cand if c["e1"]["bust"] <= live["e1"]["bust"]]
        pick = max(ok, key=lambda c: c["e1"]["inc"]) if ok else min(cand, key=lambda c: c["e1"]["bust"])
        for c in cand:
            W(f"| k={c['kelly'][0]} cap {c['kelly'][1]}{' **PICK**' if c is pick else ''} | {c['all']['q']:.2f} | {ff(c,'e1')} | {ff(c,'e2')} | {fverdict(c, live)} |")
for s in ("base", "lock"):
    W(f"\n## B2. Cushion-proportional sizing, EVAL - stream = {s}\n")
    W("Cells: pass / frozen / bust % / median sessions. cap base = largest size of the live Eval-Mode row (50K 2, 100K 4, 150K 4). PICK = best 2021-23 pass %.\n")
    for p in PL[1:]:
        live = get("E", p, s, None); cap0 = {"50K": 2, "100K": 4, "150K": 4}[p]
        W(f"\n**{p}**\n\n| rule | 2021-23 | 2024-26 | vs live |\n|---|---|---|---|")
        W(f"| LIVE eval row | {fe(live,'e1')} | {fe(live,'e2')} | - |")
        f1 = get("E", p, s, (0, 1)); W(f"| fixed 1 micro | {fe(f1,'e1')} | {fe(f1,'e2')} | {everdict(f1, live)} |")
        cand = [get("E", p, s, (k, cap0 + d)) for k in KS for d in (0, 1, 2)]
        pick = max(cand, key=lambda c: (c["e1"]["pass_"], -c["e1"]["med"]))
        for c in cand: W(f"| k={c['kelly'][0]} cap {c['kelly'][1]}{' **PICK**' if c is pick else ''} | {fe(c,'e1')} | {fe(c,'e2')} | {everdict(c, live)} |")
W("\n## C. Which account size for 1 micro? (same trades, fixed 1 micro, no brake)\n")
W("EVAL pass / frozen / bust % / median sessions (25K, 50K: 120-session window; 100K, 150K: 250). FUNDED dead % / mean / survivor / median per 2 wk. 'inc per dead pt' = mean income per 2 wk / dead %.\n")
W("| plan @ size | stream | EVAL all | EVAL 2021-23 | EVAL 2024-26 | FUNDED all | FUNDED 2021-23 | FUNDED 2024-26 | inc per dead pt |\n|---|---|---|---|---|---|---|---|---|")
for s in ("base", "lock"):
    for p in PL:
        for kel, lab in (((0, 1), "1 micro"), (None, "live table")):
            if p == "25K" and kel is None: continue
            e = get("E", p, s, kel); f = get("F", p, s, kel); a = f["all"]
            W(f"| {p} @ {lab} | {s} | {fe(e,'all')} | {fe(e,'e1')} | {fe(e,'e2')} | {ff(f,'all')} | {ff(f,'e1')} | {ff(f,'e2')} | {a['inc'] / max(a['bust'], 1):.1f} |")
open("kelly_tables_body.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))
