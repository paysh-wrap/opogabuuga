"""Tables + verdicts from results.json (run_small.py). Run: python3 report.py > tables.md
ROBUST = 5y pass >= BASE - 2 (50K also >= 59) AND judge pass >= BASE judge - 3 AND pick pass >= BASE pick - 5.
QUALIFIES (user's rule) = ROBUST AND 5y median days < BASE median AND profit >= BASE profit.  Best = lowest median days, then higher 5y pass."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(HERE + "/results.json"))


def flags(k, cn, r):
    b = R[f"{k}|{cn}|BASE"]
    rob = (r["ALL"]["pass"] >= b["ALL"]["pass"] - 2 and (k != 50 or r["ALL"]["pass"] >= 59)
           and r["JUDGE"]["pass"] >= b["JUDGE"]["pass"] - 3 and r["PICK"]["pass"] >= b["PICK"]["pass"] - 5)
    q = rob and r["ALL"]["med"] is not None and r["ALL"]["med"] < b["ALL"]["med"] and r["profit"] >= b["profit"]
    return rob, q


def row(name, r, rob, q):
    a = r["ALL"]; ch = r["chain"]
    return (f"| {name} | {a['pass']:.1f} | {a['stuck']:.1f} | {a['p60']:.1f} | {a['med']:.0f} | {ch['mean']:.0f} ({ch['cens']:.0f} %) | "
            f"{r['PICK']['pass']:.1f} | {r['JUDGE']['pass']:.1f} | {r['profit']:,.0f} | {'YES' if rob else 'no'} | {'YES' if q else 'no'} |")


HDR = ("| config | pass 5y | stuck | <=60d | median d | exp. days w/ resets (cens) | pick pass | judge pass | profit $ | ROBUST | QUALIFIES |\n"
       "|---|---|---|---|---|---|---|---|---|---|---|")


def best(k, cn):
    rows = [(n.split("|", 2)[2], r) for n, r in R.items() if n.startswith(f"{k}|{cn}|") and not n.endswith("|BASE")]
    ev = [(n, r) + flags(k, cn, r) for n, r in rows]
    qual = sorted([x for x in ev if x[3]], key=lambda x: (x[1]["ALL"]["med"], -x[1]["ALL"]["pass"]))
    rob = sorted([x for x in ev if x[2]], key=lambda x: (x[1]["ALL"]["med"], -x[1]["ALL"]["pass"]))
    fast = sorted(ev, key=lambda x: (x[1]["ALL"]["med"] or 1e9, -x[1]["ALL"]["pass"]))
    return ev, qual, rob, fast


if __name__ == "__main__":
    for k in (25, 50, 100):
        for cn in ("C40", "C50"):
            b = R[f"{k}|{cn}|BASE"]; ev, qual, rob, fast = best(k, cn)
            print(f"\n### {k}K {cn} - {len(ev)} configs, {len(rob)} ROBUST, {len(qual)} qualify "
                  f"(ROBUST: 5y >= {max(b['ALL']['pass'] - 2, 59 if k == 50 else 0):.1f}, judge >= {b['JUDGE']['pass'] - 3:.1f}, pick >= {b['PICK']['pass'] - 5:.1f})\n")
            print(HDR); print(row("**BASE**", b, True, False))
            top = qual[:5] if qual else rob[:5]
            print(f"| *top {'qualifying' if qual else 'ROBUST (none qualifies)'} by median days* |||||||||||")
            for n, r, ro, q in top: print(row(n, r, ro, q))
            print("| *fastest overall (any)* |||||||||||")
            for n, r, ro, q in fast[:3]: print(row(n, r, ro, q))
            print("\nVERDICT:", (f"best = {qual[0][0]}  cfg {qual[0][1]['cfg']}" if qual else "none"))
