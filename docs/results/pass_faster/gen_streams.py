"""Build the trade streams used by the pass-faster study (research only, no app code touched).
 NOISE base / LOCK80  : session-20 generator noise3.gen (shipped eval config: preset C, lock +100 pt -> stop entry+10, Mondays off);
                        LOCK80 = same with trigger 80 pt (lock distance still entry+10).
 CANDACE              : engine candace_ict.replay_day, D154 defaults (keep_all_sweeps ON, NY 09:30-10:00), via the study harness
                        (ctm_lib.engine_trades, 3 prior days of history).
 CONTI VWAP           : engine conti_vwap.replay_day, ContiVwapCfg() defaults (volume recovered from the stored VWAP as in session 21).
Run:  cd <worktree>/backend && NS_CACHE=<scratch>/days_vwap.json PYTHONPATH=. python3 ../docs/results/pass_faster/gen_streams.py
"""
import sys, os, json, pickle
HERE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PKL = "/tmp/claude-0/-home-user-opogabuuga/a242e4b9-b41b-5028-bba9-c21e825f6a98/scratchpad/data/days.pkl"
sys.argv = [sys.argv[0], PKL]
S20 = WT + "/docs/results/session20/strategy_review"
sys.path.insert(0, S20)
import types
_src = open(S20 + "/lib.py").read().replace('SP + "/data/days12.pkl"', repr(PKL))   # same data, other path
nlib = types.ModuleType("lib"); nlib.__file__ = S20 + "/lib.py"; sys.modules["lib"] = nlib
exec(compile(_src, S20 + "/lib.py", "exec"), nlib.__dict__)
import noise3
import pandas as pd

def noise_streams():
    base = noise3.gen()
    lock80 = noise3.gen(lock=(80.0, 10.0))
    ref = pd.read_csv(S20 + "/streams_BASE.csv")
    same = (len(ref) == len(base)) and all((ref[c].values == base[c].values).all() for c in ("d", "ek", "xk", "side")) \
        and abs(ref.pnl.values - base.pnl.values).max() < 1e-9
    print("BASE regenerated:", len(base), "trades; identical to session-20 streams_BASE.csv:", same, "net", round(base.pnl.sum(), 1))
    print("LOCK80:", len(lock80), "trades net", round(lock80.pnl.sum(), 1))
    base.to_csv(HERE + "/streams_noise_base.csv", index=False)
    lock80.to_csv(HERE + "/streams_noise_lock80.csv", index=False)

def cs_streams():
    sys.path.insert(0, WT + "/docs/results/new_strategies/candace_keep_sweeps")
    sys.path.insert(0, WT + "/docs/results/new_strategies/candace_trade_more")
    import multiprocessing as mp
    import ctm_lib as L
    from app.config import ContiVwapCfg
    import backtest_new as B
    days = L.B.load_days(); built, info = L.B.build(days); L.BUILT = built
    cfg = L.CandaceIctCfg()
    assert cfg.keep_all_sweeps is True
    pool = mp.Pool(4)
    res = L.run_all(cfg.model_dump(), mode="engine", pool=pool)
    rows = [t for ds, ts, _ in res for t in ts]
    pd.DataFrame(rows).to_csv(HERE + "/streams_candace.csv", index=False)
    print("CANDACE trades", len(rows))
    v = B.vwap_trades_all(built, ContiVwapCfg()) if hasattr(B, "vwap_trades_all") else None
    # backtest_new.vwap_trades filters ds >= START2Y; do the 5-year run here with the same row builder
    out = []
    for ds, gb, mb in built:
        for s in B.conti_vwap.replay_day(mb, ContiVwapCfg(), B.TICK):
            out.append(B.sig_row(ds, "VWAP", s.time, s.direction.name, s.direction.name, s.entry, abs(s.entry - s.stop), s.outcome,
                                 s.exit_time, s.exit_price, mb[-1].c, s.direction.sign))
    pd.DataFrame(out).to_csv(HERE + "/streams_vwap.csv", index=False)
    print("VWAP trades", len(out))
    pool.close()

if __name__ == "__main__":
    which = sys.argv_orig if hasattr(sys, "argv_orig") else None
    noise_streams()
    cs_streams()
