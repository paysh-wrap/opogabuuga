from gen import *
H = lambda t: " | ".join([st(t[t.d < "2024-01-01"], "21-23"), st(t[t.d >= "2024-01-01"], "24-26")])
v = {"BASE (lock, no Mon)": {}, "with Mondays": dict(dayskip=None), "no lock": dict(lock=None), "no lock, with Mon (paper-like)": dict(lock=None, dayskip=None),
     "look 10": dict(look=10), "look 20": dict(look=20), "step 30": dict(step=30), "maxtr 1": dict(maxtr=1), "stop $100": dict(stop_usd=100.), "stop $75": dict(stop_usd=75.)}
for k, kw in v.items():
    t = noise3.gen(**kw); print(f"{k:32s}", st(t, ""), "\n   ", H(t))
