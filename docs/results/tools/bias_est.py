"""Likely win rate WITH a daily bias of accuracy p (session 8). Uses REAL engine trades (research.py month exports)
and the market's own 1-minute data: each trade is 'with' the day if its direction matches the session's real
close-vs-open direction, else 'against'. A daily bias right p% of the time keeps the 'with' trades on the days it
is right and the 'against' trades on the days it is wrong (it blocks the other side), so
win(p) = (p·W_with + (1−p)·W_against) / (p·N_with + (1−p)·N_against), same for $ and trades.
p = 0.5 is a coin flip (no information, half the trades); p = 1.0 is a perfect oracle (impossible in practice).
usage: bias_est.py DIR CSV_1M [SESSIONS]"""
import csv
import glob
import json
import sys
from datetime import UTC, datetime

sys.path.insert(0, __file__.rsplit("/docs/", 1)[0] + "/backend")
from app.clock import session_date  # noqa: E402

d_dir, csv_path = sys.argv[1], sys.argv[2]
o, c = {}, {}
with open(csv_path) as f:
    rd = csv.reader(f)
    next(rd)
    for ts, op, _h, _l, cl, _v in rd:
        s = session_date(datetime.fromisoformat(ts.replace("Z", "+00:00"))).isoformat()
        o.setdefault(s, float(op))
        c[s] = float(cl)
day = {s: (1 if c[s] > o[s] else -1) for s in o}
grp = {"with": [], "against": []}
for f in sorted(glob.glob(f"{d_dir}/*.csv.json")):
    mon = f.rsplit("/", 1)[1][:7]
    for t in json.load(open(f))["trades"]:
        if t["pnl_usd"] is None or t["opened_at"][:7] != mon:
            continue
        at = datetime.fromisoformat(str(t["opened_at"]).replace(" ", "T"))
        s = session_date(at if at.tzinfo else at.replace(tzinfo=UTC)).isoformat()  # stored as naive UTC
        d = 1 if t["direction"] == "LONG" else -1
        grp["with" if day.get(s) == d else "against"].append(float(t["pnl_usd"]))
nw, na = len(grp["with"]), len(grp["against"])
ww, wa = sum(x > 0 for x in grp["with"]), sum(x > 0 for x in grp["against"])
pw, pa = sum(grp["with"]), sum(grp["against"])
n = nw + na
print(f"{d_dir}: {n} trades — with the day {nw} ({ww / max(nw, 1):.0%} win, ${pw:+.0f}) · against {na} "
      f"({wa / max(na, 1):.0%} win, ${pa:+.0f})")
print(f"  no bias (backtest)          {n:4d} tr  {(ww + wa) / max(n, 1):4.0%} win  ${pw + pa:+8.0f}")
for p in (0.5, 0.55, 0.6, 0.65, 1.0):
    tr = p * nw + (1 - p) * na
    win = (p * ww + (1 - p) * wa) / tr if tr else 0
    usd = p * pw + (1 - p) * pa
    label = {0.5: "coin flip", 0.55: "likely", 0.6: "good", 0.65: "very good", 1.0: "perfect (impossible)"}[p]
    print(f"  bias right {p:4.0%} ({label:20s}) {tr:6.1f} tr  {win:4.0%} win  ${usd:+8.0f}")
