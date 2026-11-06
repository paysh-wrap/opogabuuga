"""Backtest with a per-session bias: oracle (hindsight upper bound) or trend (prior closes only)."""
import sys, json, logging
from pathlib import Path
logging.disable(logging.CRITICAL)
from app.backtest.data import load_csv
from app.backtest.runner import BacktestConfig, run_backtest
from app.clock import session_date
from datetime import datetime, UTC
sym, csvp, plan, kind, mode = sys.argv[1:6]
bars = load_csv(Path(csvp).read_text())
sess = {}
for b in sorted(bars, key=lambda b: b.open_ms):
    d = session_date(datetime.fromtimestamp(b.open_ms / 1000, tz=UTC)).isoformat()
    o = sess.setdefault(d, [b.o, b.c]); o[1] = b.c
days = sorted(sess)
bias = {}
for i, d in enumerate(days):
    if kind == "oracle":
        bias[d] = "LONG_ONLY" if sess[d][1] > sess[d][0] else "SHORT_ONLY"
    else:  # trend: prior session close vs close 3 sessions earlier (no lookahead)
        if i < 4: bias[d] = "NO_TRADE"; continue
        bias[d] = "LONG_ONLY" if sess[days[i-1]][1] > sess[days[i-4]][1] else "SHORT_ONLY"
cfg = BacktestConfig(symbol=sym, bias="recorded", recorded_bias=bias, one_to_one=mode == "oo", scalp=mode == "sc", low_risk=mode == "lr")
r = run_backtest(bars, cfg, Path(plan))
pn = [float(x["pnl"]) for x in r.trades if x["pnl"] is not None]
w = sum(1 for p in pn if p > 0); g = sum(p for p in pn if p > 0); l = -sum(p for p in pn if p < 0)
print(f"{sym} {kind:6} {mode:3} trades {len(pn):3} win {w/len(pn) if pn else 0:.0%} net {sum(pn):8.1f} pf {g/l if l else float('inf'):.2f}")
