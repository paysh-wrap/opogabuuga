"""Builds tables.md from results.json (python3 report.py)."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
r = json.load(open(HERE + "/results.json"))
f = lambda x, d=0: "-" if x is None else f"{x:.{d}f}"
out = []
W = {"ALL": "5 years", "JUDGE": "judge 2024-01..2026-10", "PICK": "pick 2021-10..2023-12"}
for k in (25, 50):
    rows = ["BASE", "NOISE1"] + (["C125_1"] if k == 25 else []) + ["A", "B"]
    for w in ("ALL", "JUDGE", "PICK"):
        out.append(f"\n### {k}K, {W[w]} (rolling starts)\n")
        out.append("| row | pass % | bust % | stuck % | running % | median d | p75 d | pass <=60 d % | plan-sized $ | worst DD $ | trades/wk | n starts |")
        out.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for n in rows:
            a = r[f"{n}|{k}|roll|{w}"]; s = r[f"{n}|{k}|static|{w}"]
            if "tp" in s: prof, dd = s["tp"], s["ddp"]; tpw = sum(s["taken"].values()) / (s["ndays"] / 5.0) if isinstance(s["taken"], dict) else 0
            else: prof, dd, tpw = s["profit"], s["dd"], s["tpw"]
            out.append(f"| {n} | {f(a['pass_'],1)} | {f(a['bust'],1)} | {f(a['stuck'],1)} | {f(a['run'],1)} | {f(a['med'])} | {f(a['p75'])} | {f(a['p60'],1)} | {f(prof)} | {f(dd)} | {f(tpw,1)} | {a['n']} |")
    out.append(f"\n### {k}K trades taken / skipped (static fresh-account replay, plan-sized; N = NOISE, C = CANDACE)\n")
    out.append("| row | window | N sig/taken | C sig/taken | skipped: position open N/C | hedge N/C | no room N/C | C resized | C stop $ over 125 |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    for n in ["A", "B"]:
        for w in ("ALL", "JUDGE", "PICK"):
            c = r[f"{n}|{k}|static|{w}"]["cnt"]
            out.append(f"| {n} | {w} | {c['sig'][0]}/{c['taken'][0]} | {c['sig'][1]}/{c['taken'][1]} | {c['open'][0]}/{c['open'][1]} | {c['hedge'][0]}/{c['hedge'][1]} | {c['room'][0]}/{c['room'][1]} | {c['shrunk'][1]} | {c['over125']} |")
    # verdict
    out.append(f"\n### {k}K verdict cells (rule: pass % higher OR pass<=60 higher; stuck(+bust) not higher than BASE by > 2 pts; profit not lower than BASE)\n")
    out.append("| variant | window | pass d | <=60 d | stuck d | bust+stuck d | profit d | cell |")
    out.append("|---|---|---|---|---|---|---|---|")
    for n in [x for x in rows if x not in ("BASE",)]:
        for w in ("JUDGE", "ALL"):
            a = r[f"{n}|{k}|roll|{w}"]; b = r[f"BASE|{k}|roll|{w}"]
            sa = r[f"{n}|{k}|static|{w}"]; sb = r[f"BASE|{k}|static|{w}"]
            pa = sa["tp"] if "tp" in sa else sa["profit"]; pb = sb["tp"]
            c1 = a["pass_"] > b["pass_"] or a["p60"] > b["p60"]; c2 = a["stuck"] - b["stuck"] <= 2; c3 = pa >= pb
            fails = [x for x, ok in (("speed/pass", c1), ("stuck", c2), ("profit", c3)) if not ok]
            out.append(f"| {n} | {w} | {a['pass_']-b['pass_']:+.1f} | {a['p60']-b['p60']:+.1f} | {a['stuck']-b['stuck']:+.1f} | {(a['bust']+a['stuck'])-(b['bust']+b['stuck']):+.1f} | {pa-pb:+.0f} | {'PASS' if not fails else 'FAIL: ' + ', '.join(fails)} |")
open(HERE + "/tables.md", "w").write("\n".join(out) + "\n")
print("\n".join(out))
