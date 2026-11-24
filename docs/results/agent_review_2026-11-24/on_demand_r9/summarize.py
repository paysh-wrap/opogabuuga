"""Builds table.md from study.json (aggregates over the 20 plan x setup rows; first-payout median over rows with a payout)."""
import json, statistics as st
D = json.load(open("study.json")); modes = list(D[0]["modes"])
def agg(rows, m, key): return st.mean(r["modes"][m][key] or 0 for r in rows)
def first(rows, m): v = [r["modes"][m]["median_sessions_to_first"] for r in rows if r["modes"][m]["median_sessions_to_first"]]; return st.mean(v) if v else float("nan")
out = ["| group | mode | net/yr/acct all starts | net/yr paid-scenario | any payout % | bust % | median sessions to 1st | payouts/yr | lost trades/yr | pause days/yr |", "|---|---|---|---|---|---|---|---|---|---|"]
groups = [("ALL 20 rows", D)] + [(f"{k}K", [r for r in D if r["plan"] == k]) for k in (25, 50, 100, 150)]
for g, rows in groups:
    for m in modes:
        out.append(f"| {g} | {m} | {agg(rows,m,'year_mean'):.0f} | {agg(rows,m,'paid_year_mean'):.0f} | {agg(rows,m,'any_payout_pct'):.1f} | {agg(rows,m,'bust_pct'):.1f} | {first(rows,m):.0f} | {agg(rows,m,'payouts_mean'):.2f} | {agg(rows,m,'lost_trades_year'):.1f} | {agg(rows,m,'pause_days_year'):.1f} |")
rows_od = [r for r in D if r["modes"]["on_demand"]["any_payout_pct"] > 0]
out += ["", "Rows where on-demand pays at all (session profit >= $500 reachable): %d of %d. On those rows, net/yr/acct (all starts): " % (len(rows_od), len(D)) + ", ".join(f"{m} {agg(rows_od, m, 'year_mean'):.0f}" for m in modes)]
wins = {m: sum(1 for r in D if r["modes"][m]["year_mean"] == max(v["year_mean"] for n, v in r["modes"].items() if n in ("weekly", "2weeks", "daily_close", "on_demand"))) for m in modes}
out += ["Rows (of 20) where each mode is best net/yr (excl. the counterfactual): " + json.dumps(wins)]
open("table.md", "w").write("\n".join(out) + "\n"); print("\n".join(out))
