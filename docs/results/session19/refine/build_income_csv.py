"""B7 (session 20): rebuild the Dashboard income-projection stream from the session-19 shipped config:
NOISE preset C (+100 pt -> entry +10 lock, $250 stop) with Mondays off, plus the afternoon fade on days NOISE did not
trade, Mondays skipped too (D132). Funded accounts keep the fade (pm_fade_cfg.eval_off only affects EVAL).
Writes backend/app/backtest/data/main_strategy_s19.csv (1 micro, net of costs, 2019-05 -> 2026-11)."""
import os
import noise2, fade2

D, F, moves = noise2.data()
mon = lambda d, f: f["dow"] == 0
n = noise2.gen(dayskip=mon)
mondays = {d for d, f in F.items() if f["dow"] == 0}
fz = fade2.gen(set(n.d))
fz = fz[~fz.d.isin(mondays)]
hhmm = lambda k: "%02d:%02d" % divmod(9 * 60 + 30 + int(k), 60)
rows = [(r.d, round(r.pnl, 2), "NOISE", hhmm(r.ek)) for r in n.itertuples()] + [(r.d, round(r.pnl, 2), "FADE", hhmm(r.ek)) for r in fz.itertuples()]
rows.sort(key=lambda x: (x[0], x[3]))
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../../backend/app/backtest/data/main_strategy_s19.csv")
with open(out, "w") as fh:
    fh.write("# MAIN strategy, session-19 shipped config (D132): NOISE preset C lock +100->+10, $250 stop, Mondays off + PM fade $250 "
             "on days NOISE did not trade (Mondays off), MNQ 1 micro, Databento MNQ.v.0, 2019-05-06..2026-11-06, net of costs\n")
    fh.write("d,pnl,strategy,entry_time,causal\n")
    for d, p, s, t in rows: fh.write(f"{d},{p},{s},{t},1\n")
print(len(rows), sum(r[1] for r in rows), rows[0], rows[-1])
