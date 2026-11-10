"""Trade-stream stats (1 micro, $250 stop, net of costs): hindsight (old) vs causal (new), by era and strategy."""
import os
import pandas as pd

D = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "backend", "app", "backtest", "data"))
old = pd.read_csv(D + "/main_strategy_5y_hindsight.csv", comment="#")
new = pd.read_csv(D + "/main_strategy_5y.csv", comment="#")


def st(t):
    w = t.pnl > 0
    if not len(t):
        return "-"
    pf = t.pnl[w].sum() / -t.pnl[~w].sum()
    return f"{len(t)} / {w.mean()*100:.1f}% / PF {pf:.2f} / ${t.pnl.sum():,.0f}"


print("| slice | old (hindsight) n / win / PF / profit | new (causal) n / win / PF / profit |\n|---|---|---|")
for nm, f in (("all 2021-11..2026-10", lambda t: t), ("IS 2021-11..2023-12", lambda t: t[t.d <= "2023-12-31"]), ("HO 2024-01..2026-10", lambda t: t[t.d > "2023-12-31"])):
    print(f"| {nm} | {st(f(old))} | {st(f(new))} |")
    for s in ("NOISE", "FADE"):
        print(f"|   {s} only | {st(f(old[old.strategy == s]))} | {st(f(new[new.strategy == s]))} |")
days = 1305
print(f"\ntrades/day old {len(old)/days:.2f} new {len(new)/days:.2f}; profit per month (60 months) old ${old.pnl.sum()/60:,.0f} new ${new.pnl.sum()/60:,.0f}")
