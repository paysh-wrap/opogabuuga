"""quick landscape scan 2 (printed only): grow / brake / taper / dlock around the frontier"""
import sys, os, time, math, itertools
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sim150 as S

t0 = time.time(); rows = []
for stop, N, gr, brk, tap, dl in itertools.product((100, 150, 250), (4, 5, 6), (None, (1200, 8), (2000, 8)), (None, 0.5, 0.35), (None, (0.5, "h")), (None, 0.33)):
    if gr and gr[1] <= N: continue
    c = S.mk(stop=stop, N=N, grow=gr, brake=(brk, math.ceil(N / 2)) if brk else None, taper=(tap[0], math.ceil(N / 2)) if tap else None, dlock=dl)
    r = S.evaluate(c, with_static=False)
    a = r["ALL"]; rows.append((a["p60"], a["pass"], a["stuck"], a["run"], a["med"] or 0, S.key(c), r["JUDGE"]["pass"], r["PICK"]["pass"], r["ch"]["mean"], r["ch"]["cens"]))
print("n configs", len(rows), "time", round(time.time() - t0, 1))
ok = sorted([x for x in rows if x[1] >= 70], reverse=True)
print("meeting pass>=70:", len(ok))
for x in ok[:40]: print(f"p60 {x[0]:5.1f} pass {x[1]:5.1f} stuck {x[2]:5.1f} run {x[3]:5.1f} med {x[4]:5.0f} | judge {x[6]:5.1f} pick {x[7]:5.1f} | chain {x[8] or 0:6.1f} cens {x[9]:4.1f} | {x[5]}")
print("--- highest p60 overall")
for x in sorted(rows, reverse=True)[:15]: print(f"p60 {x[0]:5.1f} pass {x[1]:5.1f} stuck {x[2]:5.1f} run {x[3]:5.1f} med {x[4]:5.0f} | {x[5]}")
