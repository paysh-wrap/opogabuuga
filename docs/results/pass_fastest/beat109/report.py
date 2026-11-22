import json, os
H = os.path.dirname(os.path.abspath(__file__))
st = json.load(open(H + "/results.json")); bs = json.load(open(H + "/../brake150/results.json"))
out = []
for cn in ("C40", "C50"):
    b = bs[f"BASE|{cn}"]; u = bs[f"U1|{cn}"]
    jf, pf, bp = b["JUDGE"]["pass"] - 3, b["PICK"]["pass"] - 5, b["profit"]
    rows = [(k, r) for k, r in st.items() if k.endswith("|" + cn)]
    def rob(r): return r["ALL"]["pass"] >= 70 and r["JUDGE"]["pass"] >= jf and r["PICK"]["pass"] >= pf and r["profit"] >= bp
    R = [(k, r) for k, r in rows if rob(r)]
    nbeat = [k for k, r in R if r["ALL"]["med"] and r["ALL"]["med"] < u["ALL"]["med"]]
    out.append(f"\n{cn}: BASE judge {b['JUDGE']['pass']:.1f} pick {b['PICK']['pass']:.1f} profit {bp:,.0f}; U1 med {u['ALL']['med']:.0f}; floors judge>={jf:.1f} pick>={pf:.1f}; "
               f"{len(rows)} configs, {len(R)} robust, {len(nbeat)} robust with median < {u['ALL']['med']:.0f}")
    for title, sel, sk in (("by median days", R, lambda kr: (kr[1]["ALL"]["med"] or 1e9, -kr[1]["ALL"]["pass"])),
                           ("by chain days (expected days to first pass with resets)", R, lambda kr: kr[1]["chain"]["mean"])):
        out.append(f"{cn} top 5 ROBUST {title}")
        out.append("| config (stop|NOISE|CAND|brake cushion/micros|taper|grow|daylock) | pass | <=60d | median | chain d | pick | judge | profit |")
        out.append("|---|---|---|---|---|---|---|---|")
        for k, r in sorted(sel, key=sk)[:5]:
            out.append(f"| {k.rsplit('|', 1)[0]} | {r['ALL']['pass']:.1f} | {r['ALL']['p60']:.1f} | {r['ALL']['med']:.0f} | {r['chain']['mean']:.0f} | {r['PICK']['pass']:.1f} | {r['JUDGE']['pass']:.1f} | {r['profit']:,.0f} |")
    out.append(f"{cn} top 3 by median ignoring robustness")
    for k, r in sorted(rows, key=lambda kr: kr[1]["ALL"]["med"] or 1e9)[:3]:
        out.append(f"  {k.rsplit('|',1)[0]}: pass {r['ALL']['pass']:.1f} med {r['ALL']['med']:.0f} pick {r['PICK']['pass']:.1f} judge {r['JUDGE']['pass']:.1f} profit {r['profit']:,.0f}")
print("\n".join(out)); open(H + "/tables.md", "w").write("\n".join(out))
