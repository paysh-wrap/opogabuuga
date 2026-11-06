"""Research dump: run ONE backtest with the app's own engine, keep its throwaway DB, and export every PASS
candidate (features, score items, gates, plan) + every trade taken, for offline filter screening.

usage: research.py SYMBOL CSV PLAN OUT.json [days]"""
import json
import logging
import sqlite3
import sys
import tempfile
from pathlib import Path

keep: list[str] = []
_TD = tempfile.TemporaryDirectory


class TD(_TD):  # keep the backtest's throwaway DB so it can be read afterwards
    def __init__(s, *a, **k):
        super().__init__(*a, **k)
        s._finalizer.detach()
        keep.append(s.name)

    def cleanup(s):
        pass


tempfile.TemporaryDirectory = TD
logging.disable(logging.CRITICAL)
from app.backtest.data import load_csv  # noqa: E402
from app.backtest.runner import BacktestConfig, run_backtest  # noqa: E402

sym, csvp, plan, out = sys.argv[1:5]
days = int(sys.argv[5]) if len(sys.argv) > 5 else 0
bars = load_csv(Path(csvp).read_text())
if days:
    first = bars[0].open_ms
    bars = [b for b in bars if b.open_ms < first + days * 86_400_000]
r = run_backtest(bars, BacktestConfig(symbol=sym, bias="NEUTRAL"), Path(plan))
db = next(Path(k) / "bt.db" for k in keep if (Path(k) / "bt.db").exists())
c = sqlite3.connect(db)
c.row_factory = sqlite3.Row
sigs = {}
for s in c.execute("select * from signals"):
    sigs[s["id"]] = dict(s)
    sigs[s["id"]]["features"] = json.loads(s["features"] or "{}")
    sigs[s["id"]]["gates"] = {}
    sigs[s["id"]]["plans"] = []
for g in c.execute("select signal_id, gate, passed, detail from signal_gates"):
    if g["signal_id"] in sigs:
        sigs[g["signal_id"]]["gates"][g["gate"]] = {"passed": bool(g["passed"]), **json.loads(g["detail"] or "{}")}
for p in c.execute("select * from trade_plans"):
    if p["signal_id"] in sigs:
        sigs[p["signal_id"]]["plans"].append({k: p[k] for k in p.keys()})
trades = [dict(t) for t in c.execute("select * from trades order by id")]
json.dump({"symbol": sym, "plan": plan, "sessions": r.sessions, "signals": list(sigs.values()), "trades": trades,
           "skips": r.skips, "statuses": r.signals}, open(out, "w"), default=str)
print(sym, "sessions", r.sessions, "signals", len(sigs), "trades", len(trades), "->", out)
