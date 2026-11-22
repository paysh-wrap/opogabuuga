"""Tables + verdict from results.json -> tables.md (stdout too)."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(HERE + "/results.json"))
MIXES = ["BASE", "N+CANDACE", "C125", "C125_1", "C125_W1030"]
TESTS = ["C125", "C125_1", "C125_W1030"]
g = lambda m, k, meth, w: R[f"{m}|{k}|{meth}|{w}"]
f0 = lambda x: "-" if x is None else f"{x:.0f}"
out = []


def roll_cell(r): return f"{r['pass_']:.0f} / {r['bust_all']:.0f} / {r['run']:.0f}"


for meth, title in (("roll", "rolling starts"), ("boot", "session-21 bootstrap (cross-check)")):
    out.append(f"\n### Results, {title}: pass / bust+stuck / running %, median / 75th pct days, pass within 60 d %\n")
    wins = ("ALL", "JUDGE", "PICK") + (("L12",) if meth == "boot" else ())
    out.append("| plan | variant | " + " | ".join(f"{w}: P/B/R % | med / p75 d | <=60d %" for w in wins) + " |")
    out.append("|" + "---|" * (2 + 3 * len(wins)))
    for k in (25, 50):
        for m in MIXES:
            cells = []
            for w in wins:
                r = g(m, k, meth, w); cells += [roll_cell(r), f"{f0(r['med'])} / {f0(r['p75'])}", f"{r['p60']:.0f}"]
            out.append(f"| Pro {k}K | {m} | " + " | ".join(cells) + " |")

out.append("\n### Static replay: profit, CANDACE trades taken / skipped (fresh account, plan-sized NOISE, CANDACE at its variant sizing)\n")
out.append("| plan | variant | window | 1-micro $ | plan-sized $ | worst DD plan-sized $ | trades/wk | CANDACE signals | taken | sized to 0 | skipped (NOISE position open) | NOISE skipped (CANDACE open) |")
out.append("|" + "---|" * 12)
for k in (25, 50):
    for w in ("ALL", "JUDGE", "PICK"):
        for m in MIXES:
            s = g(m, k, "static", w); tk = s["taken"]; sg = s["sig"]
            tpw = (tk["0"] + tk["1"]) / s["ndays"] * 5
            out.append(f"| Pro {k}K | {m} | {w} | {s['t1']:,.0f} | {s['tp']:,.0f} | {s['ddp']:,.0f} | {tpw:.1f} | {sg['1']} | {tk['1']} | {s['size0']['1']} | {s['skip_open']['1']} | {s['skip_open']['0']} |")

out.append("\n### Verdict cells (rolling, test minus BASE; rule = median days lower OR pass higher; bust+stuck <= +2 pts; plan-sized AND 1-micro profit not lower)\n")
out.append("| variant | plan | window | d pass | d median d | d bust+stuck | d profit plan / 1-micro $ | faster or more pass | bust ok | profit ok | cell |")
out.append("|" + "---|" * 11)
tot = {}
for t in TESTS:
    for k in (25, 50):
        for w in ("JUDGE", "ALL"):
            b = g("BASE", k, "roll", w); x = g(t, k, "roll", w); sb = g("BASE", k, "static", w); sx = g(t, k, "static", w)
            a = (x["med"] is not None and b["med"] is not None and x["med"] < b["med"]) or x["pass_"] > b["pass_"]
            bo = x["bust_all"] <= b["bust_all"] + 2
            po = sx["tp"] >= sb["tp"] and sx["t1"] >= sb["t1"]
            ok = a and bo and po; tot.setdefault(t, []).append(ok)
            dm = (x["med"] - b["med"]) if x["med"] is not None and b["med"] is not None else None
            out.append(f"| {t} | {k}K | {w} | {x['pass_']-b['pass_']:+.1f} | {f0(dm) if dm is None else f'{dm:+.0f}'} | {x['bust_all']-b['bust_all']:+.1f} | {sx['tp']-sb['tp']:+,.0f} / {sx['t1']-sb['t1']:+,.0f} | {'yes' if a else 'NO'} | {'yes' if bo else 'NO'} | {'yes' if po else 'NO'} | **{'PASS' if ok else 'FAIL'}** |")
out.append("\nCells passed: " + "; ".join(f"{t} {sum(v)} of {len(v)}" for t, v in tot.items()))
open(HERE + "/tables.md", "w").write("\n".join(out)); print("\n".join(out))
