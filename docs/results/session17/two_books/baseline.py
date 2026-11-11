"""Reproduce the NOISE baselines. writes out/baseline.json + out/streams/NOISE_*.csv"""
import os, json
import core as C
HERE = os.path.dirname(os.path.abspath(__file__)); os.makedirs(HERE + "/out/streams", exist_ok=True)
D = C.load()["days"]
out = {}
for nm, kw in (("NOISE_1pct (session 9)", dict(stop_usd=None, hard_pct=0.01)), ("NOISE_250 (current app default)", dict()),
               ("NOISE_250_lock (preset C: +100 -> +10)", dict(lock=(100, 10)))):
    t = C.noise(D, **kw); t.to_csv(f"{HERE}/out/streams/{nm.split(' ')[0]}.csv", index=False)
    r = C.row(nm, t); out[nm] = r; print(C.fmt(r))
json.dump(out, open(HERE + "/out/baseline.json", "w"), indent=1)
