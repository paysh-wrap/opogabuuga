import json, math, statistics as st
import fast
def lab(c):
    s = f"{c['lo']}->{c['hi']} micros" if c['hi'] > 1 else "1 micro flat"
    if c['hi'] > 1: s += f" while cushion>={int(c['X']*100)}% MLL" + (", drop after loss" if c['droploss'] else "") + (", only while profit<50% target" if c['early'] else "")
    if c['dstop']: s += ", day-stop 35% target"
    if c['filt']: s += {"prev": ", skip day after a losing day", "tr10": ", skip if last-10-day P&L<0"}[c['filt']]
    return s
f = lambda x: "-" if x is None else f"{x:.0f}"
o = []
def P(s=""): o.append(s)
# where time goes (baseline stream, 1 micro)
days = [t for _, t in fast.tab]
by = {}
for d, t in fast.tab: by[d] = sum(x[0] for x in t) if t else None
for era, sel in (("IS", lambda d: d <= "2023-12-31"), ("HO", lambda d: d > "2023-12-31")):
    v = [x for d, x in by.items() if sel(d)]; tr = [x for x in v if x is not None]
    w = [x for x in tr if x > 0]; l = [x for x in tr if x < 0]
    P(f"- {era}: {len(v)} sessions, {len(tr)} with a trade ({100*len(tr)/len(v):.0f}%), {len(w)} winning days (avg ${st.mean(w):.0f}, max ${max(w):.0f}), {len(l)} losing days (avg ${st.mean(l):.0f}); net per session ${sum(tr)/len(v):.2f} per micro.")
stream_tbl = "\n".join(o); o.clear()
P("| plan | target | 40% cap (reading A) | min days = ceil(target / cap) | best-case days (3 profitable days needed) |"); P("|---|---|---|---|---|")
for p, (y, qm, q0) in fast.PLANS.items():
    R = fast.rules(p); cap = .4 * R["target"]; P(f"| {p} | ${R['target']:,.0f} | ${cap:,.0f} | {math.ceil(R['target']/cap)} (=2.5, so 3) | 3 |")
floor_tbl = "\n".join(o); o.clear()
for reading in "AB":
    res = json.load(open(f"out_{reading}.json"))
    P(f"\n## Reading {reading} ({'best day <= 40% of target; binding case' if reading=='A' else 'literal 40% of day-start balance; never binds - sensitivity'})\n")
    P("Columns: pass / bust / still-open(750) in %, sessions to pass p25 / median / p75 (among passers), sessions per successful pass incl. resets. HO = 2024-26, L12 = last 12 months (L12 is ~260 days: noisy).\n")
    for plan, d in res.items():
        fin = d["final"]
        rows = [(fast_c, r, picked) for fast_c, r, picked in fin]
        P(f"### {plan}\n"); P("| setting | picked on IS | HO pass/bust/open | HO p25/med/p75 | HO sess per pass | L12 pass/bust | L12 med |"); P("|---|---|---|---|---|---|---|")
        rows.sort(key=lambda t: (t[1]["HO"]["per_pass"] is None, t[1]["HO"]["per_pass"] or 0))
        base = next(t for t in rows if t[0]["hi"] == 1 and not t[0]["dstop"] and not t[0]["filt"])
        for c, r, pk in rows:
            h, l = r["HO"], r["L12"]
            P(f"| {lab(c)}{' **(baseline)**' if c is base[0] else ''} | {'yes' if pk else 'ref'} | {h['pass_']:.0f}/{h['bust']:.0f}/{h['open_']:.0f} | {f(h['p25'])}/{f(h['med'])}/{f(h['p75'])} | {f(h['per_pass'])} | {l['pass_']:.0f}/{l['bust']:.0f} | {f(l['med'])} |")
        for lim in (40, 35):
            ok = [t for t in rows if t[1]["HO"]["bust"] <= lim and t[1]["HO"]["per_pass"] and t[2] is not None]
            ok.sort(key=lambda t: t[1]["HO"]["per_pass"])
            if ok:
                c, r, pk = ok[0]; h = r["HO"]
                P(f"\nBest with HO bust <= {lim}%: **{lab(c)}** - pass {h['pass_']:.0f}%, bust {h['bust']:.0f}%, median {f(h['med'])} sessions (p25 {f(h['p25'])}, p75 {f(h['p75'])}), {f(h['per_pass'])} sessions per pass with resets; baseline: {f(base[1]['HO']['med'])} median, {f(base[1]['HO']['per_pass'])} per pass.")
            else: P(f"\nBest with HO bust <= {lim}%: **none** (every setting busts more).")
        P()
open("tables.md", "w").write(f"STREAM\n{stream_tbl}\n\nFLOOR\n{floor_tbl}\n" + "\n".join(o))
