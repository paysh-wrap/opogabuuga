import sys, statistics as st, itertools
sys.path.insert(0,'/home/user/opogabuuga/backend')
from decimal import Decimal
from pathlib import Path
from app.config import load_rules
from app.backtest.income_projection import research_days, rules_view, project, eval_view

names, dd = research_days()
DAYS = [[float(x) for x in d] for d in dd]
N = len(DAYS)
HALF = next(i for i, n in enumerate(names) if n >= "2024-01-01")
PLANS = {  # plan: (horizon, funded size, brake(frac, qty) or None)
 "25k": (120, 1, None), "50k": (120, 2, (0.5, 1)), "100k": (250, 2, (0.3, 1)), "150k": (250, 3, (0.5, 2))}
STEP = 2

def sim(days, E, rule, horizon):
    """E: start,target,mll,trig,lock,dll. Returns (status, sessions)."""
    bal = peak = E["start"]; floor = bal - E["mll"]; npos = 0
    for n, trades in enumerate(days[:horizon]):
        cush = bal - floor
        q = rule["size"](bal - E["start"], cush, E)
        br = rule["brake"]
        if br and cush < br[0] * E["mll"]: q = min(q, br[1])
        remaining = E["target"] - (bal - E["start"])
        day = 0.0
        for p in trades:
            p *= q
            if E["dll"] and day + p <= -E["dll"]: p = -E["dll"] - day
            bal += p; day += p
            if bal <= floor: return "BUST", n + 1
            if E["dll"] and day <= -E["dll"]: break
            if rule["lock"] and day >= rule["lock"] * remaining and day > 0: break
        if trades and day > 0: npos += 1
        peak = max(peak, bal)
        floor = E["lock"] if peak >= E["trig"] else max(floor, peak - E["mll"])
        if bal - E["start"] >= E["target"] and npos >= 1: return "PASS", n + 1
    return "OPEN", min(horizon, len(days))

def mkrule(b, brake, mll, kind=None, k=0, X=None, down=None, Z=None, lock=None):
    def size(prof, cush, E):
        if kind is None: return b
        if kind == "a": return b + k
        if kind == "b":
            rem = 1 - prof / E["target"]
            return (b + k) if rem > X else (down if down is not None else b)
        if kind == "d":
            return b + min(2, max(0, int(cush // (Z * E["mll"])) - 1))
        if kind == "bd":
            rem = 1 - prof / E["target"]
            return (b + min(2, max(0, int(cush // (Z * E["mll"])) - 1))) if rem > X else b
    return {"size": size, "brake": brake, "lock": lock}

def runall(E, rule, horizon, lo=0, hi=None):
    hi = N - horizon if hi is None else hi
    res = [sim(DAYS[i:i + horizon], E, rule, horizon) for i in range(lo, hi, STEP)]
    return res

def summarize(res):
    n = len(res); P = [s for t, s in res if t == "PASS"]
    return dict(n=n, pas=100 * len(P) / n, bust=100 * sum(t == "BUST" for t, _ in res) / n,
                opn=100 * sum(t == "OPEN" for t, _ in res) / n,
                med=st.median(P) if P else None,
                p75=sorted(P)[int(0.75 * (len(P) - 1) + .5)] if P else None)

def chain(E, rule, horizon):
    """restart after bust/open; sessions until first pass, starts where it resolves."""
    out = []
    for i in range(0, N - horizon, STEP):
        t = i; tot = 0; ok = False
        while t + 30 < N:
            s, d = sim(DAYS[t:t + horizon], E, rule, horizon)
            tot += d; t += d
            if s == "PASS": ok = True; break
            if t + horizon > N: break
        if ok: out.append(tot)
        elif t + horizon <= N + 0: pass
    return out

report = []
def out(s=""):
    print(s); report.append(s)

for plan, (hz, b, br) in PLANS.items():
    r = load_rules(Path(f"/home/user/opogabuuga/config/rules/lucid_pro_{plan}.yaml")).rules
    ev = eval_view(r)
    E = dict(start=float(ev.start), target=float(ev.target), mll=float(ev.mll), trig=float(ev.lock_trigger),
             lock=float(ev.lock_level), dll=float(ev.dll) if ev.dll else None)
    maxq = int(0.5 * E["mll"] // 250)
    brk = (Decimal(str(br[0])), br[1]) if br else None
    fv = float(project(rules_view(r), accounts=1, micros=b, cadence=10, brake=brk).year_mean)
    rules = {"BASE": mkrule(b, br, E["mll"])}
    for k in (1, 2):
        if b + k <= maxq: rules[f"a +{k}"] = mkrule(b, br, E["mll"], "a", k)
    for k in (1, 2):
        for X in (.3, .5):
            if b + k <= maxq: rules[f"b +{k} X{int(X*100)} ->b"] = mkrule(b, br, E["mll"], "b", k, X, None)
    for k in (1, 2):
        if b + k <= maxq: rules[f"b +{k} X50 ->1"] = mkrule(b, br, E["mll"], "b", k, .5, 1)
    for Y in (.33, .5, .75): rules[f"c Y{int(Y*100)}"] = mkrule(b, br, E["mll"], lock=Y)
    for Z in (.4, .6):
        if b + 1 <= maxq: rules[f"d Z{Z}"] = mkrule(b, br, E["mll"], "d", Z=Z)
    # summary pass 1
    rows = {}
    for nm, ru in rules.items():
        res = runall(E, ru, hz); s = summarize(res)
        s["h1"] = summarize(runall(E, ru, hz, 0, min(HALF, N - hz)))["pas"]
        s["h2"] = summarize(runall(E, ru, hz, HALF, N - hz))["pas"]
        rows[nm] = s
    # combos of best two (fastest median among those not worse than base pass-2pts), a/b/d sizing + c lock
    base = rows["BASE"]
    cand = [nm for nm, s in rows.items() if nm != "BASE" and s["med"] and s["pas"] >= base["pas"] - 2 and s["med"] < base["med"]]
    cand.sort(key=lambda n: (rows[n]["med"], -rows[n]["pas"]))
    # combo: best size-type rule + best lock rule (Y), plus top-2 sized combos
    sizers = [n for n in cand if n[0] in "abd"]; lockers = [n for n in rules if n.startswith("c ")]
    if sizers:
        for lk in sorted(lockers, key=lambda n: -rows[n]["pas"])[:1]:
            for sz in sizers[:2]:
                ru = dict(rules[sz]); ru["lock"] = rules[lk]["lock"]
                nm = f"e [{sz}]+[{lk}]"; rules[nm] = ru
                res = runall(E, ru, hz); s = summarize(res)
                s["h1"] = summarize(runall(E, ru, hz, 0, min(HALF, N - hz)))["pas"]
                s["h2"] = summarize(runall(E, ru, hz, HALF, N - hz))["pas"]
                rows[nm] = s
    for nm, ru in rules.items():
        c = chain(E, ru, hz); s = rows[nm]
        s["chain_med"] = st.median(c) if c else None; s["chain_mean"] = st.mean(c) if c else None
        s["proxy"] = s["med"] / (s["pas"] / 100) if s["med"] else None
        s["value"] = s["pas"] / 100 * fv
    out(f"\n## Pro {plan.upper()}  (target {E['target']:.0f}, MLL {E['mll']:.0f}, funded size {b}, brake {br}, horizon {hz}, max micros by 50%-MLL rule {maxq}, starts {rows['BASE']['n']})")
    out(f"Funded year-1 take-home at Regular size (1 account, bi-weekly payouts): ${fv:,.0f}")
    out("| rule | pass% | bust% | open% | med d | p75 d | pass% 21-23 | pass% 24-26 | value/eval $ | value vs base | med/pass (proxy) | restart-chain med d | restart mean d |")
    out("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    bv = rows["BASE"]["value"]; winner = None
    for nm, s in rows.items():
        ok = nm != "BASE" and s["med"] and s["value"] >= .97 * bv and s["h1"] >= base["h1"] - 2 and s["h2"] >= base["h2"] - 2
        if ok and (winner is None or (s["med"], -s["pas"]) < (rows[winner]["med"], -rows[winner]["pas"])): winner = nm
        f = lambda x, p=1: "-" if x is None else f"{x:.{p}f}"
        out(f"| {nm} | {s['pas']:.1f} | {s['bust']:.1f} | {s['opn']:.1f} | {f(s['med'],0)} | {f(s['p75'],0)} | {s['h1']:.1f} | {s['h2']:.1f} | {s['value']:,.0f} | {100*s['value']/bv:.0f}% | {f(s['proxy'],0)} | {f(s['chain_med'],0)} | {f(s['chain_mean'],0)} |")
    out(f"\nWINNER {plan}: {winner}" + (f"  -> median {rows[winner]['med']} vs base {base['med']} sessions (chain med {rows[winner]['chain_med']} vs {base['chain_med']})" if winner else " (none passes the constraints)"))
Path("report.md").write_text("# Pro eval 'Evaluation Mode' study (agentJ)\n" + "\n".join(report))
