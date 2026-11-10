"""Saves the passing streams (+ the combination) to streams/<idea>.csv and prints their stats."""
import pickle, os
import winrate_study as W, round2 as R
days = R.days
base = W.build(days); A, B = W.halves(base)
V = {"BASE": ({}, {}, None),
     "noise_lock100_plus10_no_reentry": ({"be": 100, "lock": 10, "norefire": True}, {}, None),
     "noise_lock80_plus10_no_reentry": ({"be": 80, "lock": 10, "norefire": True}, {}, None),
     "fade_after_winning_noise": ({}, {"after_noise": True}, "win"),
     "lock100_plus_fade_after_win": ({"be": 100, "lock": 10, "norefire": True}, {"after_noise": True}, "win")}
os.makedirs(W.HERE + "/streams", exist_ok=True)
for n, (nk, fk, ai) in V.items():
    t = W.build(days, nk, fk, after_if=ai); a, b = W.halves(t); v = R.verdict(a, b, A, B); s5 = W.stats(t)
    f = lambda s: f"{s['n']} | {s['win']:.1f}% | {s['pf']:.2f} | ${s['usd']:,.0f} | ${s['dd']:,.0f} | ${s['wd']:,.0f}"
    print(n, "|", f(a), "|", f(b), "|", f(s5), "|", v[0])
    if n != "BASE" and v[0] == "PASS":
        t.assign(pnl=t.pnl.round(2)).rename(columns={"pnl": "pnl_per_micro"}).to_csv(f"{W.HERE}/streams/{n}.csv", index=False)
