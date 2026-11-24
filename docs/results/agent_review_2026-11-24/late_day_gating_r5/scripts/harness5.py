"""Round-3 harness: loads the REAL fast-pass sim (pass_fastest/sim150.py + brake150/final_search/within60 patches) on /home/user/days.pkl.
Patches applied in memory to source (repo files untouched): PKL/SCR paths, brake bands, CANDACE grow, day-lock-all, NOISE lock (trigger,offset),
NOISE cost add-on (+$/micro RT), CANDACE cost (COST1)."""
import sys, os, types, json
PF = "/home/user/paytience/docs/results/pass_fastest"; PKL = "/home/user/days.pkl"; SCR = "/tmp/claude-0/r3"
MOD = SCR + "/mod"
g = open(PF + "/gen_lib.py").read()
g = g.replace('HERE = os.path.dirname(os.path.abspath(__file__))\nWT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))', 'WT = "/home/user/paytience"')
import re
g = re.sub(r'PKL = ".*"', 'PKL = "%s"' % PKL, g); g = re.sub(r'SCR = ".*"', 'SCR = "%s"' % SCR, g)
g = g.replace('kw = dict(stop_usd=float(stop), maxtr=maxtr, lock=(float(lock), 10.0))',
              'kw = dict(stop_usd=float(stop), maxtr=maxtr, lock=(tuple(map(float, lock)) if isinstance(lock, (tuple, list)) else (float(lock), 10.0)))')
open(MOD + "/gen_lib.py", "w").write(g)
sys.path.insert(0, MOD)

LEG = [None]
def load_sim():
    src = open(PF + "/sim150.py").read()
    src = src.replace('HERE = os.path.dirname(os.path.abspath(__file__))\nWT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))', 'WT = "/home/user/paytience"')
    src = re.sub(r'PKL = ".*"', 'PKL = "%s"' % PKL, src, count=1); src = re.sub(r'SCR = ".*"', 'SCR = "%s"' % SCR, src, count=1)
    # noise lock may be a (trigger, offset) tuple: file name + generator
    src = src.replace('''fn = f"{SCR}/streams/noise_s{int(stop)}_l{int(lock)}_m{maxtr}_{'M' if mon else 'x'}.csv"''',
                      '''lk_ = lock if isinstance(lock, (tuple, list)) else (lock, 10)
        fn = f"{SCR}/streams/noise_s{int(stop)}_l{int(lk_[0])}o{int(lk_[1])}_m{maxtr}_{'M' if mon else 'x'}.csv"''')
    src = src.replace('''        df = df[(df.d >= WIN["ALL"][0]) & (df.d <= WIN["ALL"][1])].copy()
        df["entry"] = [float(OPEN[d][int(k_)]) for d, k_ in zip(df.d, df.ek)]
        _cache[k] = df
    return _cache[k]


def fade_df''', '''        df = df[(df.d >= WIN["ALL"][0]) & (df.d <= WIN["ALL"][1])].copy()
        df["entry"] = [float(OPEN[d][int(k_)]) for d, k_ in zip(df.d, df.ek)]
        df["pnl"] = df["pnl"] - NADD
        _cache[k] = df
    return _cache[k]


def fade_df''')
    src = src.replace("COST1 = 2.0     #", "NADD = 0.0; COST1 = 2.0     #", 1)
    src = src.replace('fade=False, nc=0, cwin=1000, ng=0,', 'fade=False, nc=0, cwin=1000, ng=0, nbands=(), cbands=(), cgrow=None, dlall=False, gbands=(),')
    reps = [
        ('                if bb is not None and cush / MLL < bb: q = min(q, bc)\n',
         '                if bb is not None and cush / MLL < bb: q = min(q, bc)\n'
         '                for fb_, fn_ in c["nbands"]:\n'
         '                    if cush / MLL < fb_: q = min(q, fn_)\n'),
        ('                q = nc if kind == KC else ng\n',
         '                q = nc if kind == KC else ng\n'
         '                if kind == KC and c["cgrow"]:\n'
         '                    ex_ = int((bal - floor) // c["cgrow"][0]) - 1\n'
         '                    if ex_ > 0: q = min(c["cgrow"][1], nc + ex_)\n'
         '                if kind == KC:\n'
         '                    for fb_, fn_ in c["cbands"]:\n'
         '                        if (bal - floor) / MLL < fb_: q = min(q, fn_)\n'
         '                if kind == KG:\n'
         '                    for fb_, fn_ in c["gbands"]:\n'
         '                        if (bal - floor) / MLL < fb_: q = min(q, fn_)\n'),
        ('                per = b * 2.0 + 2.0 if kind == KC else b * 2.0 + 2.0\n',
         '                if c["dlall"] and (lockday or (dlk and today > 0 and rem0 > 0 and today >= dlk * rem0)):\n'
         '                    if not lockday: lockday = True; dlkd += 1\n'
         '                    continue\n'
         '                per = b * 2.0 + 2.0 if kind == KC else b * 2.0 + 2.0\n'),
    ]
    for a, b in reps:
        assert src.count(a) == 1, a
        src = src.replace(a, b)
    m = types.ModuleType("sim_r5"); m.__file__ = PF + "/sim150.py"
    exec(compile(src, m.__file__, "exec"), m.__dict__)
    g = LEG[0]
    m.gala_df = lambda: g[(g.day >= m.WIN["ALL"][0]) & (g.day <= m.WIN["ALL"][1])]
    return m

PLANS = {50: (50000., 3000., 2000., 52100., 50100., 1200., 1000.), 150: (150000., 9000., 4500., 154600., 150100., 2700., 2250.)}
MLL = {50: 2000., 150: 4500.}
def sim(k):
    S = load_sim(); S.SIZE, S.TARGET, S.MLL, S.LOCK_TRIG, S.LOCK_LVL, S.DLL0, S.CAP_TRADE = PLANS[k]
    S.CONS, ds = 40.0, 0.38; S.DSTOP = ds * S.TARGET
    return S
def cfg(k, stop, N, nc, nb=(), cb=(), grow=None, dlock=None, lock=100, taper=None, cgrow=None, dlall=False):
    f = lambda bands: tuple((d / MLL[k], m) for d, m in bands)
    lk = tuple(lock) if isinstance(lock, (tuple, list)) else (lock, 10)
    return dict(stop=stop, N=N, nc=nc, nbands=f(nb), cbands=f(cb), taper=taper, grow=grow, dlock=dlock, cwin=1000, lock=lk, brake=None, cgrow=cgrow, dlall=dlall)
BUILT = {150: dict(stop=100, N=5, nc=5, nb=((2250, 2), (1500, 1)), cb=((2700, 4), (1500, 1)), grow=(500., 6), dlock=0.7, cgrow=(1500, 6)),
         50: dict(stop=75, N=2, nc=4, nb=((667, 1),), cb=((1000, 3),), dlock=0.4, lock=80)}

def metrics(S, c):
    e = S.evaluate(S.mk(**c)); r = e["_roll"]
    out = {}
    for w in ("ALL", "PICK", "JUDGE"):
        x = e[w]; out[w] = dict(pass_=x["pass"], stuck_bust=x["stuck"], run=x["run"], med=x["med"], n=x["n"])
    out["profit"] = e["static"]["profit"]; out["dd"] = e["static"]["dd"]
    # start half-year spread (ALL starts)
    import numpy as np
    hy = {}
    for i, d in enumerate(S.DATES):
        k = d[:4] + ("H1" if int(d[5:7]) <= 6 else "H2"); hy.setdefault(k, []).append(i)
    ps = {k: 100.0 * float((r["out"][ix] == 0).mean()) for k, ix in hy.items()}
    out["hy"] = ps; v = list(ps.values()); out["hy_min"], out["hy_med"], out["hy_max"] = min(v), float(np.median(v)), max(v)
    return out
