"""quick landscape scan (stop x micros, brake half@50 %), printed only - not part of the results"""
import sys, os, time, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sim150 as S

t0 = time.time()
print("stop  N  | pass stuck run | p30 p45 p60 | med p75 | chain mean/att(cens%) | profit dd tpw")
for stop in (75, 100, 150, 200, 250, 300):
    for N in (2, 3, 4, 6, 8):
        c = S.mk(stop=stop, N=N, brake=(0.5, math.ceil(N / 2)))
        r = S.evaluate(c)
        a = r["ALL"]; ch = r["ch"]
        print(f"{stop:4d} {N:2d} | {a['pass']:5.1f} {a['stuck']:5.1f} {a['run']:5.1f} | {a['p30']:4.1f} {a['p45']:4.1f} {a['p60']:4.1f} | {a['med'] or 0:5.0f} {a['p75'] or 0:5.0f} | {ch['mean'] or 0:6.1f}/{ch['att'] or 0:4.2f} ({ch['cens']:4.1f}) | {r['static']['profit']:7.0f} {r['static']['dd']:6.0f} {r['static']['tpw']:3.1f}", flush=True)
print("time", round(time.time() - t0, 1))
