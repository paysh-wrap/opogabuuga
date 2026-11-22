"""within60 study driver (research only). Reuses ../smaller_plans/run_small.py (plan constants, brake150 size bands) + ../sim150.py.
dll=False: DLL0=0 and LucidScale off (no daily loss limit); every other rule unchanged. Consistency C40 (day stop 38 %) only."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); PF = os.path.dirname(HERE)
sys.path.insert(0, PF); sys.path.insert(0, PF + "/brake150"); sys.path.insert(0, PF + "/smaller_plans")
import run_small as R
import brake150 as B
R.PLANS[150] = (150000., 9000., 4500., 154600., 150100., 2700., 2250.)
T3 = 1 / 3.0
_S = {}


def sim(k, dll):
    if (k, dll) not in _S:
        S = B.load_sim()
        S.SIZE, S.TARGET, S.MLL, S.LOCK_TRIG, S.LOCK_LVL, S.DLL0, S.CAP_TRADE = R.PLANS[k]
        S.CONS, ds = B.CONS["C40"]; S.DSTOP = ds * S.TARGET
        if not dll: S.DLL0 = 0.0; S.SCALE = False
        _S[(k, dll)] = S
    return _S[(k, dll)]


def mkcfg(stop, N, nc, nb=(), cb=(), taper=None, grow=None, dlock=None, cwin=1000, lock=100, brake=None):
    """nb/cb: tuples of (cushion fraction of MLL, micros) bands for NOISE / CANDACE"""
    return dict(stop=stop, N=N, nc=nc, nbands=tuple(nb), cbands=tuple(cb), taper=taper, grow=grow, dlock=dlock, cwin=cwin, lock=lock, brake=brake)


def ev(job):
    k, dll, name, cfg = job
    S = sim(k, dll); e = S.evaluate(S.mk(**cfg))
    r = {w: {x: e[w][x] for x in ("pass", "stuck", "run", "p60", "med")} for w in ("ALL", "PICK", "JUDGE")}
    r["chain"] = {x: e["ch"][x] for x in ("mean", "med", "cens")}
    r["profit"] = e["static"]["profit"]
    return f"{k}|{int(dll)}|{name}", r
