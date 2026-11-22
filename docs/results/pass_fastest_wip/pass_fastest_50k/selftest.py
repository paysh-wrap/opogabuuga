"""Extra validation of the parts of lib50 that the old studies cannot check (static replay, fade handling, day lock / taper, renewal chain, bootstrap).
Run: cd <worktree>/backend && PYTHONPATH=. /usr/local/bin/python3 ../docs/results/pass_fastest_50k/selftest.py
"""
import sys, os, json, time, copy
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, HERE + "/../pass_faster_100"); sys.path.insert(0, HERE + "/../pass_faster_fixed"); sys.path.insert(0, HERE + "/../pass_faster_c125")
import numpy as np
import lib50 as L
F = L.F
ref = json.load(open(HERE + "/../pass_faster_100/results.json"))
okk = True


def chk(name, cond):
    global okk
    okk &= bool(cond); print(("  OK   " if cond else "  FAIL ") + name)


print("A) static replay vs stored (pass_faster_100/results.json, 50K, 5y)")
for nm, c, key in (("BASE", L.BASE, "BASE|50|static|ALL"), ("N100", L.NOISE2_100, "N100|50|static|ALL"), ("A", L.ROW_A, "A|50|static|ALL")):
    st = L.static(L.build_days(c), c, "ALL"); old = ref[key]
    if nm == "BASE": a, b = st["profit"], st["dd"]; ra, rb = old["tp"], old["ddp"]
    else: a, b = st["profit"], st["dd"]; ra, rb = old["profit"], old["dd"]
    print(f"   {nm}: profit {a:.1f} / {ra:.1f}  dd {b:.1f} / {rb:.1f}  trades/wk {st['tpw']:.2f}")
    chk(f"static {nm} profit and drawdown equal the stored values", abs(a - ra) < 1e-6 and abs(b - rb) < 1e-6)

print("B) legacy session-21 sim2 with the fade (hindsight rule, fade treated like NOISE incl. D57 shrink): per-path equality on the session-21 bootstrap paths")
import types
sys.path.insert(0, L.WT + "/docs/results/session21/pro_rules")
import sim2 as S2
S2.PKL = L.F.PKL; S2.R = L.WT + "/"; S2.S21 = None
import sim as S1
S1.R = L.WT + "/"
t = S2.load(); nf = S2.load_fade(t)
S2.GMIN = S2.smin(float(t[t.d >= "2025-11-06"].entry.mean()))
pl = S1.load_plans()["lucid_pro_50k"]
tab = S2.day_table(nf, "all")
paths = S2.make_paths(len(tab))
row = pl["tabs"]["regular"]
cc = L.cfg_of(nn=2, bb=0.5, bc=1, fade=1, fsh=1)
days = L.build_days(cc, fade_hindsight=True); ct = L.sim_tuple(cc); gm = L.gmin()
# sim2's day table spans bdate_range('2021-10-21','2026-10-30') (1,285 business days incl. holidays); lib50 uses the 1,252 trading days -> compare per path on a table built the same way
dates_bd = [d.strftime("%Y-%m-%d") for d in __import__("pandas").bdate_range(*S2.ERAS["all"])]
bymap = {d: days[i] for i, d in enumerate(L.ALL_D)}
days_bd = [bymap.get(d, ()) for d in dates_bd]
bad = 0; passes = 0
for pth in paths:
    r_old = S2.sim_path(tab, pth, pl, row, True, gmin=S2.GMIN)
    r_new = L.sim_a(days_bd, pth, L.P, ct, gm)
    if r_old[0] != r_new[0] or r_old[1] != r_new[1]: bad += 1
    passes += r_old[0] == "pass"
print(f"   paths {len(paths)}, differing {bad}, old passes {passes}")
chk("fade (hindsight) + shrink path-by-path equal to sim2", bad == 0)
fo = sum(1 for x in nf.itertuples() if x.risk == 250.0) - len(t)
print(f"   fade rows in the legacy table: {fo}; in lib50 hindsight table: {sum(1 for tl in days for x in tl if x[2] == 2)}")
chk("same number of fade rows", fo == sum(1 for tl in days for x in tl if x[2] == 2))

print("C) day lock / taper / grow scenario checks (synthetic days)")
P0 = copy.deepcopy(L.P)
mk = lambda pnl, ek=60.0, risk=250.0, mae=10.0: (ek, ek + 30.5, 0, pnl, mae, risk, 20000.0, 1)
# day 0: two winners of +$300/micro at 2 micros (= +$600 each); day lock 0.33 x remaining 3000 = 990 -> second trade skipped after the first (+600 < 990 -> still trades) check both ways
days = [(mk(300.0, 60.0), mk(300.0, 200.0)), (mk(-1.0, 60.0),)]
TGT = L.P["target"]
for dl, expect_today in ((0.0, 1140.0), (0.2, 600.0)):
    c = L.cfg_of(nn=2, dl=dl); ct = L.sim_tuple(c)
    # reach into the simulator through a tiny wrapper: run one day and read the balance via a pass-through target of 1 dollar
    p1 = dict(L.P); p1["target"] = 1.0; p1["cons"] = 0
    r = L.sim_a(days, range(0, 1), p1, ct, L.gmin())
    chk(f"day lock {dl}: session 1 result {r[0]} in {r[1]} day(s)", r[0] == "pass")
# direct state check: replicate with a probe returning bal through monkeypatching sim_a's pass condition is overkill -> count taken trades with a counter strategy
def run_day(c, p, daylist):
    ct = L.sim_tuple(c); balances = []
    p2 = dict(p)
    # use cap hits as probe: with day_stop 1140 the second trade (+600 +600 = 1200) is capped
    return L.sim_a(daylist, range(0, len(daylist)), p2, ct, L.gmin())
r0 = run_day(L.cfg_of(nn=2, dl=0.0), L.P, days)
r1 = run_day(L.cfg_of(nn=2, dl=0.2), L.P, days)
chk("no day lock: second +$600 trade is taken and capped at the 38 % day stop (cap hit = 1)", r0[2] == 1)
chk("day lock 0.2 (stop at +$600 = 20 % of $3,000): second trade skipped, no cap hit", r1[2] == 0)

print("D) renewal chain on a synthetic result list")
o = np.array([1, 1, 0, 3, 0], dtype=np.int8); n = np.array([2, 1, 5, 9, 4], dtype=np.int32)
ch = L.chain(o, n)   # start0: stuck after 2 -> restart at idx2 -> pass in 5 => 7 days, 2 attempts; start1: stuck 1 -> idx2 pass 5 => 6, 2; start2: 5, 1; start3 open -> censored; start4: 4,1
chk("chain mean days = (7+6+5+4)/4 = 5.5", abs(ch["ch_days"] - 5.5) < 1e-9)
chk("chain mean attempts = (2+2+1+1)/4 = 1.5", abs(ch["ch_att"] - 1.5) < 1e-9)
chk("censored share = 1/5 = 20 %", abs(ch["ch_cens"] - 20.0) < 1e-9)

print("E) bootstrap protocol reproduces pass_faster/results.json BASE|50|boot|*")
pf = json.load(open(HERE + "/../pass_faster/results.json"))
days = L.build_days(L.BASE)
for w in ("ALL", "PICK", "JUDGE"):
    b = L.boot(days, L.BASE, w); o_ = pf[f"BASE|50|boot|{w}"]
    print(f"   {w}: pass {b['pass_']:.2f}/{o_['pass_']:.2f} stuck {b['stuck']:.2f}/{o_['stuck']:.2f} <=60d {b['p60']:.2f}/{o_['p60']:.2f} med {b['med']}/{o_['med']}")
    chk(f"BASE bootstrap {w} equals the stored one", all(abs((b[k] or 0) - (o_[k] or 0)) < 1e-9 for k in ("pass_", "stuck", "run", "p60", "med", "p75")))
print("SELFTEST", "PASSED" if okk else "FAILED")
