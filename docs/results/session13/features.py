"""Session 13: per-minute Big Beluga MSO (trend / divergence age) and LunqFX fractal (stage / direction) states on 5y MNQ RTH bars.
Real indicator code, closed bars, continuous over days. usage: python3 features.py JOB   (mso1|mso5|fr15|fr60)  -> feat_JOB.pkl"""
import sys, pickle
from datetime import datetime
from decimal import Decimal as D
from zoneinfo import ZoneInfo
import numpy as np
ROOT = "/home/user/opogabuuga"
sys.path[:0] = [ROOT + "/backend", ROOT + "/docs/results/session12"]
import ob_study as S
from app.indicators.bars import Bar
from app.indicators.bigbeluga_mso import MsoEngine
from app.indicators.lunqfx_fractal import FractalEngine
ET = ZoneInfo("America/New_York"); M = 60_000
job = sys.argv[1]
days, _ = S.load()
INF = 10**6
out = {}
if job.startswith("mso"):
    n = int(job[3:]); eng = MsoEngine(); g = 0; lb = lbe = -INF
    for d, a in days:
        base = int(datetime.fromisoformat(d + "T09:30:00").replace(tzinfo=ET).timestamp() * 1000)
        db = S.DayBars(a, None); bars = db.m
        tr = np.zeros(390, np.int8); ab = np.full(390, INF, np.int32); ae = np.full(390, INF, np.int32); buf = []
        for k in range(390):
            b = bars[k]; bb = Bar(base + k * M, base + (k + 1) * M, b.o, b.h, b.l, b.c)
            buf.append(bb)
            if (k + 1) % n == 0:
                agg = Bar(buf[0].open_ms, buf[-1].close_ms, buf[0].o, max(x.h for x in buf), min(x.l for x in buf), buf[-1].c); buf = []
                for ev in eng.push(agg):
                    if ev.event == "MSO_DIV":
                        if ev.direction == "LONG": lb = g + k
                        else: lbe = g + k
            tr[k] = {"BULL": 1, "BEAR": -1, "NONE": 0}[eng.trend]
            ab[k] = min(INF, g + k - lb); ae[k] = min(INF, g + k - lbe)   # age (min) of last bullish / bearish divergence
        out[d] = (tr, ab, ae); g += 390
else:
    h = int(job[2:]); eng = FractalEngine(h, D("0.25"))
    for d, a in days:
        base = int(datetime.fromisoformat(d + "T09:30:00").replace(tzinfo=ET).timestamp() * 1000)
        db = S.DayBars(a, None); st = np.zeros(390, np.int8); dr = np.zeros(390, np.int8)
        for k in range(390):
            b = db.m[k]; eng.push(Bar(base + k * M, base + (k + 1) * M, b.o, b.h, b.l, b.c))
            st[k] = eng.stage; dr[k] = eng._dir
        out[d] = (st, dr)
pickle.dump(out, open(f"{ROOT}/docs/results/session13/feat_{job}.pkl", "wb"))
print(job, "done", len(out))
