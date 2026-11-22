"""Validation: (1) NOISE-only through pf_sim == session-21 sim2 (bootstrap, all eras, 25K/50K); (2) float fit sizing == Decimal lucid_fit."""
import sys, random
from decimal import Decimal as Dc
import pf_sim as F
sys.path.insert(0, F.WT + "/docs/results/session21/pro_rules")
import sim2
from app.engine.lucid_fit import contracts_for, trade_risk_usd, grade_contracts
dates, op = F.trading_days()
P = F.load_plans(); t, t80, c, v = F.load_streams()
by = F.build_table(t)
gmin = F.smin(float(t[t.d >= '2025-11-06'].entry.mean()))
ok = True
for k in (25, 50):
    for era, w in (("all", "ALL"), ("is", "IS"), ("j", "L12")):
        r = F.run_boot(by, w, P[k], gmin)
        # sim2 reference
        sim2.R = F.WT + "/"; sim2.GMIN = gmin
        tab = sim2.day_table(t, era); paths = sim2.make_paths(len(tab))
        ref = sim2.run_cfg(tab, paths, F.S21.load_plans()[f"lucid_pro_{k}k"], F.S21.load_plans()[f"lucid_pro_{k}k"]["tabs"]["regular"], False)
        same = abs(r["pass_"] - ref["pass"]) < 1e-9 and abs(r["bust_all"] - ref["bust"]) < 1e-9 and abs((r["med"] or 0) - ref["days"]) < 1e-9
        print(k, era, "pf_sim", round(r["pass_"], 2), round(r["bust_all"], 2), r["med"], "| sim2", round(ref["pass"], 2), round(ref["bust"], 2), ref["days"], "SAME" if same else "DIFF")
        ok &= same
# fit sizing
rnd = random.Random(1); bad = 0
for _ in range(20000):
    k = rnd.choice((25, 50)); p = P[k]; fit = p["fitC"] if rnd.random() < .5 else p["fitV"]
    stop = rnd.choice([25.0, rnd.uniform(2, 40)]); stop = round(stop * 4) / 4
    left = rnd.choice([None, rnd.uniform(-50, p["dll"])]); room = rnd.uniform(-20, p["mll"]); gm = rnd.choice([None, 0.5, 1.0, 2.0])
    r = trade_risk_usd(Dc(p["mll"]), Dc(str(fit[0])), fit[2], None if left is None else Dc(str(round(left, 2))), Dc(str(fit[1])), Dc(str(round(room, 2))), Dc(str(p["cap_trade"])), Dc(str(p["day_stop"])))
    cc = min(contracts_for(r, Dc(str(stop)), Dc("0.25"), Dc(str(p["tv"])), Dc(str(p["fee"])), p["slip"]), p["maxmicros"])
    if gm is not None and gm < 2.0: cc = grade_contracts(cc, Dc(str(gm)))
    mine = F.fit_contracts(p, fit, stop, gm, None if left is None else round(left, 2), round(room, 2))
    bad += (mine != cc)
print("fit sizing mismatches vs Decimal functions:", bad, "of 20000"); ok &= bad == 0
print("VALIDATION", "OK" if ok else "FAILED")
