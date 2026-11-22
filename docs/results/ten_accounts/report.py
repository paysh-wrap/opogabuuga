import json, os
H = os.path.dirname(os.path.abspath(__file__)); R = json.load(open(H + "/results.json"))


def g(k, f, v, w): return R[str((k, f, v, w))]


def row(k, f, v, w):
    r = g(k, f, v, w)
    return (f"| {k}K | {'FAST' if f else 'TODAY'} | {r['passed']} | {r['resets']}/{r['bought']} | ${r['fees']:,.0f} | {r['funded_alive']}/{r['funded_lost']}/{r['to_live']} "
            f"| ${r['payouts']:,.0f} | **${r['net']:,.0f}** | {r['med_first']} |")


out = []
for w, nm in ((False, "on-demand payouts (main)"), (True, "weekly Friday payouts")):
    for v, t in (("5y", "5-year run (2021-10 to 2026-10, all 10 accounts start day 1)"), ("12m", "Last 12 months (fresh start)")):
        out += [f"### {t} - {nm}", "", "| Plan | Setup | Evals passed | Resets/replacement buys | Fees paid | Funded alive/lost/reached 5 payouts | Payouts (90 %) | Net (payouts - fees) | Median days to funded |",
                "|--|--|--|--|--|--|--|--|--|"]
        out += [row(k, f, v, w) for k in (25, 50, 100, 150) for f in (False, True)]; out.append("")
    out += [f"### Rolling 12-month starts (every 21 sessions) - {nm}", "", "| Plan | Setup | Windows | Net median | Net worst | Net best | Windows with net > 0 | Median evals passed |", "|--|--|--|--|--|--|--|--|"]
    for k in (25, 50, 100, 150):
        for f in (False, True):
            r = g(k, f, "roll", w)
            out.append(f"| {k}K | {'FAST' if f else 'TODAY'} | {r['n']} | ${r['net_med']:,.0f} | ${r['net_min']:,.0f} | ${r['net_max']:,.0f} | {100*r['pos']:.0f} % | {r['pass_med']} |")
    out.append("")
open(H + "/tables.md", "w").write("\n".join(out)); print("\n".join(out))
