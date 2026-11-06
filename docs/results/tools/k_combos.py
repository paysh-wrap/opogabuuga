"""Results K: combined Scalp variants (hour exclusion + hold time + structure). usage: k_combos.py KDIR H1 H2"""
import sys
from decimal import Decimal as D

sys.path.insert(0, "/home/user/paytience/docs/results/tools")
from scalpsim import candidates, load, run, stats  # noqa: E402

K, h1, h2 = sys.argv[1], sys.argv[2].split(","), sys.argv[3].split(",")
halves = []
for ms in (h1, h2):
    months = load(K, ms)
    halves.append(([c for mo in months for c in candidates(mo)], sum(mo.res["sessions"] for mo in months)))


def row(name, filt=lambda c: True, **kw):
    cells = []
    for cs, ns in halves:
        s = stats(run(cs, filt=lambda c: c["profile"] == "TIGHT" and filt(c), max_consec=2, **kw), ns)
        cells.append(f"{s['n']} · {s['tpd']:.2f} · {s['win']:.0%} · {s['pf']:.2f} · {s['net']:+.0f} · {s['dd']:.0f}"
                     if s["n"] else "0")
    print(f"| {name} | {cells[0]} | {cells[1]} |", flush=True)


NO713 = lambda c: c["hour"] not in (7, 13)  # noqa: E731
NO7 = lambda c: c["hour"] != 7  # noqa: E731
row("baseline")
row("skip 07:xx ET", NO7)
row("skip 07:xx + 13:xx ET", NO713)
row("skip 07 + 13, time stop 5 min", NO713, hold=5)
row("skip 07 + 13, no time stop", NO713, no_time_stop=True)
row("skip 07, no time stop", NO7, no_time_stop=True)
row("skip 07, no time stop, fixed TP all", NO7, no_time_stop=True, fixed_tp_all=True)
row("skip 07 + 13, no time stop, fixed TP all", NO713, no_time_stop=True, fixed_tp_all=True)
row("skip 07 + 13, no time stop, target 1R", NO713, no_time_stop=True, target_r=D("1.0"))
row("skip 07 + 13, no time stop, trail 1R", NO713, no_time_stop=True, trail_r=D("1.0"))
row("skip 07, time stop 5 min, C1 ≥ 0.8×ATR", lambda c: NO7(c) and c["c1atr"] >= 0.8, hold=5)
