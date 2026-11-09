import sys, io, contextlib
import numpy as np, pandas as pd
R = "/home/user/opogabuuga/docs/results"
sys.path[:0] = [R + "/tools", R + "/session10"]
import noise_area as NA, sim25k, one_year_compare as OY, addons_1y as AD
CSV = "/tmp/claude-0/-home-user-opogabuuga/528f0293-22e9-5e48-80a8-65343eb6ade7/scratchpad/data/mnq_5y.csv"
START, END = "2021-11-01", "2026-10-30"
PV, TICK, FEE = 2.0, 0.25, 1.0

def noise_t(days, look=14, step=60, hard=0.01, maxtr=3):
    moves = np.array([np.abs(a["close"] / a["open"][0] - 1) for _, a in days])
    checks = set(range(29, 360, step)); out = []
    for i in range(look, len(days)):
        d, a = days[i]
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        pc = days[i - 1][1]["close"][389]
        if np.isnan(pc) or abs(o[0] / pc - 1) > 0.015: continue
        sig = np.nanmean(moves[i - look:i], axis=0)
        ub = max(o[0], pc) * (1 + sig); lb = min(o[0], pc) * (1 - sig)
        st = dict(pos=0, entry=None, ek=None); ntr = pending = 0; hs = None
        def close_trade(px, k):
            out.append((d, st["pos"], st["entry"], px, (px - st["entry"]) * st["pos"] * PV - FEE, st["ek"], k)); st["pos"] = 0
        for k in range(390):
            if np.isnan(c[k]): continue
            if pending and st["pos"] == 0:
                st["entry"] = o[k] + pending * TICK; st["pos"], pending = pending, 0; st["ek"] = k
                hs = st["entry"] - st["pos"] * hard * st["entry"] if hard else None
            pos = st["pos"]
            if pos and hs is not None and ((pos > 0 and l[k] <= hs) or (pos < 0 and h[k] >= hs)):
                close_trade((min(hs, o[k]) if pos > 0 else max(hs, o[k])) - pos * TICK, k)
            if st["pos"] and k == 389: close_trade(c[k] - st["pos"] * TICK, k)
            if k in checks:
                pos = st["pos"]
                if pos:
                    trail = max(ub[k], vw[k]) if pos > 0 else min(lb[k], vw[k])
                    if (pos > 0 and c[k] < trail) or (pos < 0 and c[k] > trail):
                        nk = k + 1
                        close_trade((o[nk] if nk < 390 and not np.isnan(o[nk]) else c[k]) - pos * TICK, nk if nk < 390 else k)
                if st["pos"] == 0 and ntr < maxtr:
                    side = 1 if c[k] > ub[k] else (-1 if c[k] < lb[k] else 0)
                    if side: pending, ntr = side, ntr + 1
    return pd.DataFrame(out, columns=["d", "side", "entry", "exit", "pnl", "ek", "xk"])

def od_t(days, i):
    d, a = days[i]
    o, h, l, c = a["open"], a["high"], a["low"], a["close"]
    pc = days[i - 1][1]["close"][389]
    if np.isnan(pc) or abs(o[0] / pc - 1) > 0.015: return None
    rngs = [np.nanmax(x["high"]) - np.nanmin(x["low"]) for _, x in days[max(0, i - 14):i]]
    if len(rngs) < 10: return None
    move = c[29] - o[0]
    if move == 0 or abs(move) < 0.35 * np.mean(rngs): return None
    s = 1 if move > 0 else -1
    ext = np.nanmax(h[:30]) if s > 0 else np.nanmin(l[:30])
    leg = abs(ext - o[0]); entry = ext - s * 0.382 * leg; stop = ext - s * 0.786 * leg; tgt = ext
    fill = None
    for k in range(30, 181):
        if (s > 0 and l[k] <= entry - TICK) or (s < 0 and h[k] >= entry + TICK): fill = k; break
    if fill is None: return None
    for k in range(fill, 210):
        if (s > 0 and l[k] <= stop) or (s < 0 and h[k] >= stop):
            return d, s, entry, stop - s * TICK, (stop - s * TICK - entry) * s * PV - FEE, fill, k
        if (s > 0 and h[k] >= tgt) or (s < 0 and l[k] <= tgt):
            return d, s, entry, tgt, (tgt - entry) * s * PV - FEE, fill, k
    px = c[209] - s * TICK
    return d, s, entry, px, (px - entry) * s * PV - FEE, fill, 209

def walk2(s, e, stop, tgt, H, L, O, C, j0, j1):
    for j in range(j0, j1):
        if (s > 0 and L[j] <= stop) or (s < 0 and H[j] >= stop):
            px = (min(stop, O[j]) if s > 0 else max(stop, O[j])) - s * TICK
            return (px - e) * s * PV - FEE, j
        if (s > 0 and H[j] >= tgt) or (s < 0 and L[j] <= tgt):
            return (tgt - e) * s * PV - FEE, j
    return (C[j1 - 1] - s * TICK - e) * s * PV - FEE, j1 - 1

def pm_t(days, noise_days):
    out = []
    for d, a in days:
        if d < START or d in noise_days: continue
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        for k in range(210, 359):
            if np.isnan(c[k]) or np.isnan(vw[k]): continue
            sd = np.nanstd(c[:k + 1] - vw[:k + 1])
            if sd <= 0: continue
            s = -1 if c[k] > vw[k] + 2 * sd else (1 if c[k] < vw[k] - 2 * sd else 0)
            if not s: continue
            e = o[k + 1] + s * TICK; tgt = vw[k]
            if (tgt - e) * s < 4 * TICK: break
            p, j = walk2(s, e, e - s * 2 * sd, tgt, h, l, o, c, k + 1, 386)
            out.append((d, s, e, np.nan, p, k + 1, j)); break
    return pd.DataFrame(out, columns=["d", "side", "entry", "exit", "pnl", "ek", "xk"])

def ov_t(raw):
    # same as addons_1y.overnight but returns pnl only; times not needed (never overlap RTH)
    o = AD.overnight(raw); o = o[o.d >= START].copy(); o["ek"] = -1; o["xk"] = -1; return o

def combine(parts):
    t = pd.concat(parts, ignore_index=True)
    t["ord"] = t.ek
    t = t.sort_values(["d", "ord"], kind="stable")
    keep = []; last = {}
    for r in t.itertuples():
        if r.ek < 0: keep.append(True); continue
        if r.d in last and r.ek < last[r.d]: keep.append(False); continue
        keep.append(True); last[r.d] = r.xk
    return t[keep][["d", "pnl"]].reset_index(drop=True)

def stats(t, ndays):
    if not len(t): return dict(n=0)
    w = t.pnl > 0; eq = t.pnl.cumsum(); gl = -t.pnl[~w].sum()
    return dict(n=len(t), tpd=len(t) / ndays, win=w.mean(), avg=t.pnl.mean(), tot=t.pnl.sum(),
                pf=t.pnl[w].sum() / gl if gl else float("inf"), dd=(eq - eq.cummax()).min(), wd=t.groupby("d").pnl.sum().min())

def simsum(res):
    n = len(res); ps = [r for r in res if r[0] == "pass"]; bs = sum(r[0] == "bust" for r in res)
    full = [r for r in ps if not r[4]]
    pay1 = sum(r[3] >= 1 for r in full) / max(1, len(full)); ev = np.mean([r[2] for r in full]) if full else 0
    return dict(pass_=len(ps) / n, bust=bs / n, med=np.median([r[1] for r in ps]) if ps else float("nan"), pay1=pay1, paid=ev, val=ev * len(ps) / n, nfull=len(full))

def main():
    days = NA.load_days(CSV)
    raw = pd.read_csv(CSV, parse_dates=["timestamp"]).set_index("timestamp"); raw.index = raw.index.tz_convert("America/New_York")
    notes = []
    # --- verification
    orig = NA.run(days, 14, 60, 0.01, 3); nt = noise_t(days)
    ok1 = len(orig) == len(nt) and abs(orig.pnl.sum() - nt.pnl.sum()) < 1e-6 and np.allclose(orig.pnl.values, nt.pnl.values)
    rows = [r for i in range(14, len(days)) if (r := OY.open_drive(days, i))]
    od_orig = pd.DataFrame(rows, columns=["d", "side", "entry", "exit", "pnl"])
    od = pd.DataFrame([r for i in range(14, len(days)) if (r := od_t(days, i))], columns=["d", "side", "entry", "exit", "pnl", "ek", "xk"])
    ok2 = len(od_orig) == len(od) and np.allclose(od_orig.pnl.values, od.pnl.values)
    AD.START = START
    nd0 = set(nt[nt.d >= START].d)
    pm_orig = AD.pm_fade(days, nd0); pm = pm_t(days, nd0)
    ok3 = len(pm_orig) == len(pm) and np.allclose(pm_orig.pnl.values, pm.pnl.values)
    print("VERIFY noise", ok1, len(orig), orig.pnl.sum(), "| od", ok2, len(od_orig), od_orig.pnl.sum(), "| pm", ok3, len(pm_orig), pm_orig.pnl.sum())
    assert ok1 and ok2 and ok3
    f = lambda t: t[(t.d >= START) & (t.d <= END)]
    nt, od, pm = f(nt), f(od), f(pm); ov = f(ov_t(raw))
    nsess = sum(1 for d, _ in days if START <= d <= END)
    sets = {
        "NOISE": [nt], "OPEN_DRIVE": [od], "PM_FADE": [pm], "OVERNIGHT": [ov],
        "NOISE+OPEN_DRIVE": [nt, od], "NOISE+PM_FADE": [nt, pm], "NOISE+OD+PM": [nt, od, pm], "NOISE+OD+PM+OVN": [nt, od, pm, ov]}
    H1 = ("2021-11-01", "2023-12-31"); H2 = ("2024-01-01", "2026-10-30")
    nsH = [sum(1 for d, _ in days if a <= d <= b) for a, b in (H1, H2)]
    out = {}; dropped = {}
    for name, parts in sets.items():
        t = combine(parts) if len(parts) > 1 else parts[0][["d", "pnl"]].reset_index(drop=True)
        t = t.sort_values("d", kind="stable").reset_index(drop=True) if len(parts) == 1 else t
        dropped[name] = sum(len(p) for p in parts) - len(t)
        fn = f"set_{name.replace('+', '_')}.csv"; t.to_csv(fn, index=False)
        r = dict(all=stats(t, nsess), years={}, halves={}, sim={})
        dt = pd.to_datetime(t.d)
        for y, g in t.groupby(dt.dt.year): r["years"][y] = (g.pnl.sum(), g.pnl[g.pnl > 0].sum() / max(1e-9, -g.pnl[g.pnl <= 0].sum()), len(g))
        for hn, (a, b), ns in zip(("H1", "H2"), (H1, H2), nsH):
            g = t[(t.d >= a) & (t.d <= b)]; r["halves"][hn] = stats(g, ns)
        for lab, a, b in (("5y", START, END), ("H1", *H1), ("H2", *H2)):
            res = sim25k.run("Pro", fn, q=1, dll_funded=600, start=a, end=b)
            r["sim"][lab] = simsum(res)
        out[name] = r
        print(name, r["all"], dropped[name])
    # --- report
    L = [f"# Agent B: MNQ 5y combination study (1 micro, {START} to {END}, {nsess} sessions)\n",
         "Verification: my time-recording copies of NOISE, OPEN_DRIVE, PM_FADE reproduce the originals exactly "
         f"(NOISE {len(orig)} trades all-period / total ${orig.pnl.sum():.0f}; OPEN_DRIVE {len(od_orig)} / ${od_orig.pnl.sum():.0f}; PM_FADE(START {START}) {len(pm_orig)} / ${pm_orig.pnl.sum():.0f}); trade-by-trade pnl identical.\n",
         "Overlap rule: sorted by entry bar per day; a trade is dropped if it enters before the previous kept trade exits (greedy, earlier entry wins). OVERNIGHT never overlaps. PM_FADE is generated only on days NOISE-alone did not trade (original definition). Sim: sim25k Pro, eval no DLL, funded DLL $600, rolling starts every 2 days; Halves sims run on the half's dates only.\n",
         "## Headline (whole period)\n", "| Set | trades | /day | win% | $/trade | total $ | PF | maxDD $ | worst day $ | dropped (overlap) |", "|---|---|---|---|---|---|---|---|---|---|"]
    for n, r in out.items():
        s = r["all"]; L.append(f"| {n} | {s['n']} | {s['tpd']:.2f} | {s['win']:.1%} | {s['avg']:.2f} | {s['tot']:.0f} | {s['pf']:.2f} | {s['dd']:.0f} | {s['wd']:.0f} | {dropped[n]} |")
    L += ["\n## Per-year total $ (PF)  [2021 = Nov-Dec only, 2026 = Jan-Oct]\n", "| Set | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |", "|---|---|---|---|---|---|---|"]
    for n, r in out.items():
        cells = []
        for y in range(2021, 2027):
            v = r["years"].get(y); cells.append(f"{v[0]:.0f} ({v[1]:.2f}){' LOSS' if v[0] < 0 else ''}" if v else "-")
        L.append(f"| {n} | " + " | ".join(cells) + " |")
    L += ["\n## Halves\n", "| Set | H1 trades | H1 win% | H1 $/tr | H1 total $ | H1 PF | H1 maxDD | H2 trades | H2 win% | H2 $/tr | H2 total $ | H2 PF | H2 maxDD |", "|---|" + "---|" * 12]
    for n, r in out.items():
        a, b = r["halves"]["H1"], r["halves"]["H2"]
        L.append(f"| {n} | {a['n']} | {a['win']:.1%} | {a['avg']:.2f} | {a['tot']:.0f} | {a['pf']:.2f} | {a['dd']:.0f} | {b['n']} | {b['win']:.1%} | {b['avg']:.2f} | {b['tot']:.0f} | {b['pf']:.2f} | {b['dd']:.0f} |")
    L += ["\n## Pro 25K sim\n", "| Set | period | eval pass | bust | median eval days | >=1 payout | avg paid $ | value/eval $ | funded n |", "|---|---|---|---|---|---|---|---|---|"]
    for n, r in out.items():
        for lab in ("5y", "H1", "H2"):
            s = r["sim"][lab]; L.append(f"| {n} | {lab} | {s['pass_']:.1%} | {s['bust']:.1%} | {s['med']:.0f} | {s['pay1']:.1%} | {s['paid']:.0f} | {s['val']:.0f} | {s['nfull']} |")
    L += ["\n## 'Helps' test vs NOISE alone (pass rate AND total profit higher in BOTH halves)\n", "| Set | H1 pass vs N | H2 pass vs N | H1 $ vs N | H2 $ vs N | helps? |", "|---|---|---|---|---|---|"]
    base = out["NOISE"]
    for n, r in out.items():
        if n == "NOISE": continue
        c = [r["sim"][h]["pass_"] > base["sim"][h]["pass_"] for h in ("H1", "H2")] + [r["halves"][h]["tot"] > base["halves"][h]["tot"] for h in ("H1", "H2")]
        L.append(f"| {n} | {r['sim']['H1']['pass_']:.1%} / {base['sim']['H1']['pass_']:.1%} | {r['sim']['H2']['pass_']:.1%} / {base['sim']['H2']['pass_']:.1%} | {r['halves']['H1']['tot']:.0f} / {base['halves']['H1']['tot']:.0f} | {r['halves']['H2']['tot']:.0f} / {base['halves']['H2']['tot']:.0f} | {'YES' if all(c) else 'no'} |")
    open("report.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))
main()
