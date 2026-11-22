import sys, os, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_lib as G
t0 = time.time(); a = G.noise_stream(100); print("gen $100", len(a), round(time.time() - t0, 1), "s")
t0 = time.time(); b = G.noise_stream(300, lock=80.0, maxtr=2, mondays=True); print("gen $300 lock80 max2 mon", len(b), round(time.time() - t0, 1), "s")
