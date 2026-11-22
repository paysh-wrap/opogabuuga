"""Builds tables.md + stream stats from results.json and the NOISE streams (python3 report.py)."""
import json, os
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
r = json.load(open(HERE + "/results.json"))
f = lambda x, d=0: "-" if x is None else f"{x:,.{d}f}"
W = {"ALL": "5 years", "JUDGE": "judge 2024-01..2026-10", "PICK": "pick 2021-10..2023-12"}
RNG = {"ALL": ("2021-10-21", "2026-10-30"), "JUDGE": ("2024-01-01", "2026-10-30"), "PICK": ("2021-10-21", "2023-12-31")}
NAMES = {"BASE": "BASE (shipped)", "N100": "NOISE@$100 alone", "A": "A one at a time", "B": "B both at once"}
SZ = {25: "NOISE 2 + CANDACE 1", 50: "NOISE 2 + CANDACE 1", 100: "NOISE 4 + CANDACE 2", 150: "NOISE 4 + CANDACE 2"}
out = []
ver = []
for k in (25, 50, 100, 150):
    for w in ("ALL", "JUDGE", "PICK"):
        out.append(f"\n### {k}K ({SZ[k]}), {W[w]} (rolling starts)\n")
        out.append("| row | pass % | bust % | stuck % | running % | median d | p75 d | pass <=60 d % | plan-sized $ | worst DD $ | trades/wk | n starts |")
        out.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for n in NAMES:
            a = r[f"{n}|{k}|roll|{w}"]; s = r[f"{n}|{k}|static|{w}"]
            if "tp" in s: prof, dd, tpw = s["tp"], s["ddp"], sum(s["taken"].values()) / (s["ndays"] / 5.0)
            else: prof, dd, tpw = s["profit"], s["dd"], s["tpw"]
            out.append(f"| {NAMES[n]} | {f(a['pass_'],1)} | {f(a['bust'],1)} | {f(a['stuck'],1)} | {f(a['run'],1)} | {f(a['med'])} | {f(a['p75'])} | {f(a['p60'],1)} | {f(prof)} | {f(dd)} | {f(tpw,1)} | {a['n']} |")
    out.append(f"\n### {k}K trades taken / skipped (static fresh-account replay; N = NOISE, C = CANDACE)\n")
    out.append("| row | window | N sig/taken | C sig/taken | skipped: position open N/C | opposite-dir (hedge) N/C | no room N/C | C resized |")
    out.append("|---|---|---|---|---|---|---|---|")
    for n in ("N100", "A", "B"):
        for w in ("ALL", "JUDGE", "PICK"):
            c = r[f"{n}|{k}|static|{w}"]["cnt"]
            out.append(f"| {n} | {w} | {c['sig'][0]}/{c['taken'][0]} | {c['sig'][1]}/{c['taken'][1]} | {c['open'][0]}/{c['open'][1]} | {c['hedge'][0]}/{c['hedge'][1]} | {c['room'][0]}/{c['room'][1]} | {c['shrunk'][1]} |")
    out.append(f"\n### {k}K verdict cells (pass % higher OR pass<=60 higher; stuck not > BASE+2 pts; profit not lower than BASE)\n")
    out.append("| variant | window | pass d | <=60 d | stuck d | profit d | cell |")
    out.append("|---|---|---|---|---|---|---|")
    for n in ("N100", "A", "B"):
        cells = {}
        for w in ("JUDGE", "ALL"):
            a = r[f"{n}|{k}|roll|{w}"]; b = r[f"BASE|{k}|roll|{w}"]
            sa = r[f"{n}|{k}|static|{w}"]; pa = sa["profit"]; pb = r[f"BASE|{k}|static|{w}"]["tp"]
            c1 = a["pass_"] > b["pass_"] or a["p60"] > b["p60"]; c2 = a["stuck"] - b["stuck"] <= 2; c3 = pa >= pb
            fails = [x for x, ok in (("pass/speed", c1), ("stuck", c2), ("profit", c3)) if not ok]
            cells[w] = ("PASS" if not fails else "FAIL: " + ", ".join(fails))
            out.append(f"| {n} | {w} | {a['pass_']-b['pass_']:+.1f} | {a['p60']-b['p60']:+.1f} | {a['stuck']-b['stuck']:+.1f} | {pa-pb:+,.0f} | {cells[w]} |")
        ver.append((k, n, cells["JUDGE"], cells["ALL"]))
out.append("\n### Verdict summary\n")
out.append("| plan | row | judge | 5y |\n|---|---|---|---|")
for k, n, j, a in ver: out.append(f"| {k}K | {NAMES[n]} | {j} | {a} |")

# NOISE per-micro stream stats: $100 stop vs $250 stop (net of fees, per micro)
def st(df, a, b):
    d = df[(df.d >= a) & (df.d <= b)]; wins = d.pnl[d.pnl > 0].sum(); loss = -d.pnl[d.pnl < 0].sum()
    return len(d), 100 * (d.pnl > 0).mean(), wins / loss, d.pnl.sum()
n250 = pd.read_csv(HERE + "/../pass_faster/streams_noise_base.csv"); n100 = pd.read_csv(HERE + "/streams_noise_stop100.csv")
out.append("\n### NOISE stream per micro: $100 stop vs shipped $250 stop (generator-level, no account rules)\n")
out.append("| window | stop | trades | win % | PF | net $ per micro |\n|---|---|---|---|---|---|")
for w in ("ALL", "PICK", "JUDGE"):
    for nm, df in (("$250", n250), ("$100", n100)):
        n, wr, pf, net = st(df, *RNG[w]); out.append(f"| {w} | {nm} | {n} | {wr:.1f} | {pf:.2f} | {net:,.0f} |")
open(HERE + "/tables.md", "w").write("\n".join(out) + "\n")
print("\n".join(out))
