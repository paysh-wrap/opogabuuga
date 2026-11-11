"""builds the tables of RESULTS.md from out/*.json (python3 report.py > out/tables.md)"""
import json, core as C
L = lambda p: json.load(open(f"out/{p}.json"))
b, c1, c2, d, rb, fi = L("baseline"), L("c1"), L("c2"), L("d"), L("robust"), L("finish")
def T(title, rows):
    print(f"\n#### {title}\n"); print(C.HDR); [print(C.fmt(r)) for r in rows]
T("T0 NOISE baselines (reproduced)", list(b.values()) + [fi["always long 09:31 -> 16:00"], fi["always short 09:31 -> 16:00"]])
pick = lambda rows, nm: [r for r in rows if r["name"] == nm]
T("T1 Connors day-direction bias traded 09:31 -> 16:00 (all 18 variants)", c1["bias"]["rows"])
print("\nBias hit rate vs RTH open->close direction (IS / HO): " + "; ".join(f"{k}: {v['IS']['hit']:.1f}% of {v['IS']['days']} / {v['HO']['hit']:.1f}% of {v['HO']['days']}" for k, v in c1["bias"]["hits"].items()))
T("T2 Connors rules as NOISE filters (all 22)", c1["filter"]["rows"])
T("T3 Connors intraday on 5m/15m bars - IS pick + top-5 by IS PF", pick(c1["intraday"]["rows"], c1["intraday"]["pick"]) + sorted([r for r in c1["intraday"]["rows"] if r["IS"]["n"] >= 100 and r["name"] != c1["intraday"]["pick"]], key=lambda r: -r["IS"]["pf"])[:5])
T("T4 Candlestick Bible intraday (96 variants) - top-8 by IS PF", sorted([r for r in c2["rows"] if r["IS"]["n"] >= 150], key=lambda r: -r["IS"]["pf"])[:8])
print(f"\nCandlestick summary: {c2['summary']}")
T("T5 Markov day bias traded 09:31 -> 16:00", d["markov_bias"]["rows"])
print("\nIS transition tables (P(today up | state)), states = terciles of yesterday's close-to-close return D/F/U: M1 " + json.dumps(d["markov_bias"]["tables"]["M1 (yesterday's state)"]) + " | M2 " + json.dumps(d["markov_bias"]["tables"]["M2 (last two days' states)"]))
T("T6 Markov as NOISE filter", d["markov_filter"]["rows"])
T("T7 Markov as NOISE sizing (2 micros when Markov agrees)", d["markov_sizing"]["rows"])
T("T8 Intraday Markov (30-minute states)", d["markov_intraday"]["rows"])
T("T9 Combinations K1-K12 (book + Markov + NOISE)", d["combos"]["rows"] + [fi["NOISE+lock, only 'no short after RSI2 > 90'"], fi["NOISE+lock, only 'no long after RSI2 < 10'"]])
print("\n#### T10 Robustness of the momentum guard (threshold perturbation; IS eval = 2019-06..2023-12 starts)\n")
print("| variant | IS trades / PF | IS eval pass / bust | HO trades | HO win | HO PF | HO net $ | HO max DD $ | HO eval pass / bust / median days | HO strict pass / bust | net $ by year |\n|---|---|---|---|---|---|---|---|---|---|---|")
for k, v in rb["rows"].items():
    print(f"| {k} | {v['IS']['n']} / {v['IS']['pf']:.2f} | {v['ev_is']['pass_']:.1f}% / {v['ev_is']['bust']:.1f}% | {v['HO']['n']} | {v['HO']['win']:.1f}% | {v['HO']['pf']:.2f} | {v['HO']['net']:+,.0f} | {v['HO']['dd']:,.0f} | {v['ev']['pass_']:.1f}% / {v['ev']['bust']:.1f}% / {v['ev']['med']:.0f} | {v['evs']['pass_']:.1f}% / {v['evs']['bust']:.1f}% | " + ", ".join(f"{y}: {n:+,}" for y, n in v["years"].items()) + " |")
