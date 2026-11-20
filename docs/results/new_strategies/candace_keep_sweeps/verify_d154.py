"""D154 check on all 1266 days: new engine keep_all=False == the D149 engine; keep_all=True == study V1 (cks_lib).
Result 2026-11-20: OFF vs D149 engine 0 mismatches (100 trades); ON vs study V1 0 mismatches (310 trades).
Run (from backend/):  git show 5085c99:backend/app/engine/candace_ict.py > <dir>/candace_old.py, copy this script into
<dir>, then  NS_CACHE=<scratch>/days_vwap.json ../.venv/bin/python <dir>/verify_d154.py <days.pkl>"""
import sys, os, importlib.util
REPO = "/home/user/opogabuuga"
SP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO + "/docs/results/new_strategies/candace_keep_sweeps")
sys.argv = [sys.argv[0], sys.argv[1]]
import cks_lib as K
import ctm_lib as L
from app.engine import candace_ict as NEW
spec = importlib.util.spec_from_file_location("candace_old", SP + "/candace_old.py")
OLD = importlib.util.module_from_spec(spec); sys.modules["candace_old"] = OLD; spec.loader.exec_module(OLD)

def sig_keys(r):
    return [(s.time, s.direction, s.entry, s.stop, s.take_profit, s.grade, s.outcome, s.exit_time, s.exit_price) for s in r.signals]

days = L.B.load_days()
built, _ = L.B.build(days)
L.BUILT = built
on = L.CandaceIctCfg()
off = on.model_copy(update={"keep_all_sweeps": False})
assert on.keep_all_sweeps is True
bad_off = bad_on = n_old = n_on = 0
for i, (ds, gb, mb) in enumerate(built):
    h = L._hist(i)
    a, b = OLD.replay_day(h, mb, off, L.TICK), NEW.replay_day(h, mb, off, L.TICK)
    n_old += len(a.signals)
    if sig_keys(a) != sig_keys(b):
        bad_off += 1
        if bad_off <= 3: print("OFF mismatch", ds)
    eng = L.engine_trades(h, mb, on, L.TICK)
    v1 = K.run_day_v(h, mb, on, L.TICK, "V1")["signals"]
    n_on += len(eng)
    if not L.same(eng, v1):
        bad_on += 1
        if bad_on <= 3: print("ON mismatch", ds, len(eng), len(v1))
print(f"days {len(built)} | OFF vs old engine mismatches {bad_off} (old trades {n_old}) | ON vs study V1 mismatches {bad_on} (trades {n_on})")
