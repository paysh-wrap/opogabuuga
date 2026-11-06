"""Results K report: baseline + filter / management / Asia variants of MNQ Scalp (Pro 25K, neutral bias).
usage: k_report.py KDIR FIRST_HALF_MONTHS(comma) SECOND_HALF_MONTHS(comma) [asia]"""
import sys
from decimal import Decimal as D

sys.path.insert(0, "/home/user/paytience/docs/results/tools")
from scalpsim import candidates, load, run, stats  # noqa: E402

K, h1, h2 = sys.argv[1], sys.argv[2].split(","), sys.argv[3].split(",")
ASIA = len(sys.argv) > 4
sub = "/asia" if ASIA else ""
halves = []
for ms in (h1, h2):
    months = load(K, ms, sub)
    cs = [c for mo in months for c in candidates(mo)]
    halves.append((cs, sum(mo.res["sessions"] for mo in months), [m.res for m in months]))

TIGHT = lambda c: c["profile"] == "TIGHT"  # noqa: E731
NORMAL_H = lambda c: (6 * 60 + 45 <= c["hm"] < 16 * 60)  # noqa: E731  normal windows (06:45–15:30 ET)


def row(name, filt=lambda c: True, **kw):
    out = []
    for cs, ns, _ in halves:
        tr = run(cs, filt=lambda c: TIGHT(c) and filt(c), max_consec=2, **kw)
        out.append(stats(tr, ns))
    al = {"n": out[0]["n"] + out[1]["n"]}
    cells = []
    for s in out:
        if s["n"]:
            cells.append(f"{s['n']} · {s['tpd']:.2f} · {s['win']:.0%} · {s['pf']:.2f} · {s['net']:+.0f} · {s['dd']:.0f}")
        else:
            cells.append("0")
    print(f"| {name} | {cells[0]} | {cells[1]} |", flush=True)
    return out


def real():
    for cs, ns, res in halves:
        tr = [{"usd": float(t["pnl_usd"]), "r": 0} for r in res for t in r["trades"] if t["pnl_usd"] is not None]
        s = stats(tr, ns)
        print("REAL engine", ns, "sessions", s)


print("| variant | H1: trades · /day · win · PF · net $ · maxDD $ | H2: same |")
print("|---|---|---|")
if ASIA:
    real()
    row("normal hours only (same run)", NORMAL_H)
    row("normal + Asia 18:00–02:00")
    row("Asia only", lambda c: not NORMAL_H(c))
    for h in (18, 19, 20, 21, 22, 23, 0, 1):
        row(f"Asia hour {h:02d}", lambda c, h=h: c["hour"] == h)
    sys.exit()
real()
row("baseline (sim)")
for h in range(6, 16):
    row(f"hour {h:02d} only", lambda c, h=h: c["hour"] == h)
row("structure break required", lambda c: c["brk"])
row("CHoCH required", lambda c: c["choch"])
row("osc strength item > 0", lambda c: c["osc_strong"])
row("CISD before C2 close", lambda c: c["cisd_early"])
row("HTF MSO agrees", lambda c: c["htf"])
for s in (80, 85, 90):
    row(f"score ≥ {s}", lambda c, s=s: c["score"] >= s)
for v in (0.6, 0.8, 1.0):
    row(f"C1 range ≥ {v}×ATR", lambda c, v=v: c["c1atr"] >= v)
for v in (25, 50, 75):
    row(f"ATR pct ≤ {v}", lambda c, v=v: 0 <= c["atr_pct"] <= v)
for v in (2, 4, 8):
    row(f"stop buffer +{v} ticks", buf_ticks=v)
for v in (0.25, 0.5, 1.0):
    row(f"stop buffer +{v}×ATR(1m)", buf_atr=v)
for v in ("0.1", "0.2", "0.3"):
    row(f"entry deeper by {v}R", depth_r=D(v))
for v in ("0.25", "0.5"):
    row(f"BE after +{v}R", be_at=D(v))
row("no 0.30R lock (1 contract)", lock=False)
for hb in (2, 3, 5):
    row(f"time stop {hb} min (max_hold_s {hb * 60})", hold=hb)
for t in ("0.3", "0.4", "0.75", "1.0"):
    row(f"target {t}R", target_r=D(t))
print("\n-- Q4 hold winners --")
row("fixed TP 0.5R on all contracts (no runner)", fixed_tp_all=True)
row("current: half 0.5R, half runner 2R trail 0.5R (≥2 contracts)")
row("runner also on 1-contract trades (BE+trail after 0.5R)", all_runner=True)
for rr in ("1.0", "1.5", "3.0"):
    row(f"runner target {rr}R", runner_r=D(rr))
for tr_ in ("0.25", "1.0"):
    row(f"runner trail {tr_}R", trail_r=D(tr_))
row("runner trail 1.0R, target 3R, also 1-contract", all_runner=True, runner_r=D("3.0"), trail_r=D("1.0"))
row("no time stop at all (fixed 0.5R TP / stop)", fixed_tp_all=True, no_time_stop=True)
