"""CANDACE keep-sweeps study (MEASURE + REPORT only; no app code changed).
Run: cd backend && NS_CACHE=<own scratch>/days_vwap.json PYTHONPATH=. /home/user/opogabuuga/.venv/bin/python \
        ../docs/results/new_strategies/candace_keep_sweeps/run_cks.py <days.pkl> [outdir]
Protocol: pick on IS 2021-10-01..2023-12-31, judge on J 2024-01-01..2026-10-30. Writes tables.md.
"""
import sys, os, json, pickle, time, statistics
from collections import Counter, defaultdict
import multiprocessing as mp

HERE = os.path.dirname(os.path.abspath(__file__))
PKL = next(a for a in sys.argv[1:] if a.endswith(".pkl"))
OUT = next((a for a in sys.argv[1:] if os.path.isdir(a)), HERE)
sys.argv = [sys.argv[0], PKL]
sys.path.insert(0, HERE)
import cks_lib as K
import cks_stats as S
import ctm_lib as L
from ctm_lib import BASEV

PLANK = (25, 50, 100, 150)
BASE_CFG = L.CandaceIctCfg().model_dump()


def cfg_with(**kw):
    d = dict(BASE_CFG)
    d.update(kw)
    L.CandaceIctCfg(**d)
    return d


def f0(x): return f"{x:,.0f}"
def fpf(x): return "inf" if x == float("inf") else f"{x:.2f}"


X = type("X", (), {})()


def period(trs, lo, hi):
    return [t for ds in sorted(trs) if lo <= ds <= hi for t in trs[ds]]


def evaluate(trs, cnt):
    out = {}
    for pn, (lo, hi) in (("IS", (L.IS_START, L.IS_END)), ("J", (L.J_START, "2099-01-01"))):
        ts = period(trs, lo, hi)
        m = dict(s1=L.stats1(ts, X.cost, X.months[pn]), n=len(ts))
        for k in PLANK:
            m[f"fit{k}"] = S.fit2(k, ts, BASEV, X.cost)
            m[f"ev{k}"] = S.eval2(k, ts, BASEV, X.daylist, lo, hi if pn == "IS" else X.daylist[-1], X.cost)
        out[pn] = m
    # 10 chunks over the 5 years
    n = len(X.daylist)
    ch = []
    for c in range(10):
        a, b = c * n // 10, (c + 1) * n // 10
        dl = X.daylist[a:b]
        ts = [t for d in dl for t in trs.get(d, [])]
        s1 = L.stats1(ts, X.cost, max(1, len(dl) / 21.0))
        f25 = S.fit2(25, ts, BASEV, X.cost)
        f50 = S.fit2(50, ts, BASEV, X.cost)
        ch.append((dl[0], dl[-1], s1, f25["total"], f50["total"]))
    out["chunks"] = ch
    # win rate by entry half-hour (by the minute of the entry bar)
    hh = defaultdict(lambda: [0, 0])
    for t in period(trs, L.IS_START, "2099"):
        k = (t["idx"] - 1) // 30
        u = t["pts1m"] * L.PV - X.cost
        hh[k][0] += 1
        hh[k][1] += u > 0
    out["hh"] = dict(hh)
    out["cnt"] = cnt
    return out


def run_row(policy, over, pool):
    cfgd = cfg_with(**over)
    res = K.run_all(cfgd, policy, pool)
    trs = {ds: t for ds, t, _ in res}
    cnt = Counter()
    for _, _, c in res:
        if c:
            cnt.update(c)
    return trs, cnt, res


def truncated_check(policy, over, ndays=20):
    """signals at time t must depend only on bars <= t: replay truncated at each signal time."""
    cfg = L.CandaceIctCfg(**cfg_with(**over))
    bad = 0
    chk = 0
    days_used = 0
    for i in range(len(L.BUILT)):
        if days_used >= ndays:
            break
        ds, gb, mb = L.BUILT[i]
        h = L._hist(i)
        full = K.run_day_v(h, mb, cfg, L.TICK, policy)["signals"]
        if not full:
            continue
        days_used += 1
        key = lambda s: (s["time"], s["dir"], s["entry"], s["stop"], s["tp"], s["grade"])
        for s in full:
            tcut = s["time"]
            sub = [b for b in mb if b.close_time.astimezone(L.ET).strftime("%H:%M") <= tcut]
            part = K.run_day_v(h, sub, cfg, L.TICK, policy)["signals"]
            want = [key(x) for x in full if x["time"] <= tcut]
            got = [key(x) for x in part]
            chk += 1
            if want != got:
                bad += 1
    return days_used, chk, bad


def main():
    t0 = time.time()
    days = L.B.load_days()
    built, info = L.B.build(days)
    L.BUILT = built
    L.load_plans()
    X.daylist = [b[0] for b in built]
    X.cost = L.B.cost1(L.PLANS[25])
    isd = [d for d in X.daylist if d <= L.IS_END]
    jd = [d for d in X.daylist if d >= L.J_START]
    X.months = {"IS": L.months_between(isd[0], isd[-1]), "J": L.months_between(jd[0], jd[-1])}
    pool = mp.Pool(4)
    md = [f"Data: {len(X.daylist)} RTH days {X.daylist[0]}..{X.daylist[-1]}; IS = {isd[0]}..{isd[-1]} ({len(isd)} days, {X.months['IS']} months), "
          f"J = {jd[0]}..{jd[-1]} ({len(jd)} days, {X.months['J']} months). Cost ${X.cost:.2f} per micro RT, $2/pt. History = 3 prior days.\n"]

    # ---- validation
    eng_tr, eng_cnt, eng = run_row("ENGINE", {}, pool)
    mir = L.run_all(cfg_with(), (False, False, False), "mirror", pool)
    bad_m = [a for (a, x, _), (b, y, _) in zip(eng, mir) if not L.same(x, y)]
    rep_tr, rep_cnt, rep = run_row("REPLACE", {}, pool)
    bad_r = [a for (a, x, _), (b, y, _) in zip(eng, rep) if not L.same(x, y)]
    nb = sum(len(v) for v in eng_tr.values())
    md.append(f"## Validation\n\n- ctm_lib mirror vs engine replay_day (BASE): mismatching days = {len(bad_m)} of {len(X.daylist)}; BASE signals {nb} "
              f"(IS {len(period(eng_tr, L.IS_START, L.IS_END))}, J {len(period(eng_tr, L.J_START, '2099'))}).\n"
              f"- this study's generic multi-episode code in REPLACE mode vs engine: mismatching days = {len(bad_r)} of {len(X.daylist)}.\n")
    assert not bad_m and not bad_r

    # ---- variants at 10:00
    VAR = [("V1", "KEEP_ALL"), ("V2", "SAME_SIDE"), ("V3", "PROTECT_FORMED")]
    rows = {}
    rows["BASE"] = evaluate(eng_tr, eng_cnt)
    store = {"BASE": eng_tr}
    for vid, name in VAR:
        trs, cnt, _ = run_row(vid, {}, pool)
        store[vid] = trs
        rows[vid] = evaluate(trs, cnt)
        print(vid, "done", time.time() - t0, rows[vid]["IS"]["n"], rows[vid]["J"]["n"], flush=True)
    # ---- determinism
    md.append("- no-lookahead check (20 days with signals per variant; replay truncated at every signal time, signals up to t must be identical): ")
    det = []
    for vid, name in VAR:
        du, chk, bad = truncated_check(vid, {})
        det.append(f"{vid} {du} days / {chk} cut points / {bad} differences")
    md.append("; ".join(det) + "\n")

    def is_ok(res, b):
        I, bI = res["IS"], b["IS"]
        c = dict(more=I["n"] > bI["n"], pf=I["s1"]["pf"] >= 1.10,
                 t1=I["s1"]["total"] >= bI["s1"]["total"] - 1e-9,
                 t25=I["fit25"]["total"] >= bI["fit25"]["total"] - 1e-9,
                 t50=I["fit50"]["total"] >= bI["fit50"]["total"] - 1e-9)
        c["ok"] = all(c.values())
        return c

    def jcheck(res, b):
        bj, x = b["J"], res["J"]
        c = dict(t1=x["s1"]["total"] >= bj["s1"]["total"] - 1e-9, t25=x["fit25"]["total"] >= bj["fit25"]["total"] - 1e-9,
                 t50=x["fit50"]["total"] >= bj["fit50"]["total"] - 1e-9, pf=x["s1"]["pf"] > 1, n=x["n"] >= bj["n"],
                 p25=x["ev25"]["pas"] >= bj["ev25"]["pas"] - 2 and x["ev25"]["bust"] <= bj["ev25"]["bust"] + 2,
                 p50=x["ev50"]["pas"] >= bj["ev50"]["pas"] - 2 and x["ev50"]["bust"] <= bj["ev50"]["bust"] + 2)
        c["ACCEPT"] = all(c.values())
        return c

    elig = {vid: is_ok(rows[vid], rows["BASE"]) for vid, _ in VAR}
    ranked = sorted([v for v, _ in VAR if elig[v]["ok"]], key=lambda v: -rows[v]["IS"]["fit25"]["total"])
    pick = ranked[0] if ranked else None

    # ---- 10:30 for eligible variants
    ext_rows = {}
    if ranked:
        trs, cnt, _ = run_row("ENGINE", dict(ny_window="09:00-10:30"), pool)
        store["BASE@1030"] = trs
        rows["BASE@1030"] = evaluate(trs, cnt)
        for v in ranked:
            trs, cnt, _ = run_row(v, dict(ny_window="09:00-10:30"), pool)
            store[f"{v}@1030"] = trs
            rows[f"{v}@1030"] = evaluate(trs, cnt)
            ext_rows[f"{v}@1030"] = (is_ok(rows[f"{v}@1030"], rows["BASE"]), is_ok(rows[f"{v}@1030"], rows["BASE@1030"]))

    ids = list(rows)
    names = {"BASE": "engine as is", "V1": "KEEP_ALL", "V2": "SAME_SIDE", "V3": "PROTECT_FORMED"}
    lab = lambda i: i + " " + names.get(i.split("@")[0], "") + (" window 10:30" if "@" in i else "")

    def row1(i):
        out = []
        for pn in ("IS", "J"):
            s = rows[i][pn]["s1"]
            out.append(f"{s['n']} | {s['pm']:.2f} | {s['win']:.1f} | {fpf(s['pf'])} | {s['avg']:.1f} | {f0(s['total'])} | {f0(s['mdd'])}")
        return f"| {lab(i)} | " + " | ".join(out) + " |\n"

    md.append("\n## Table A: 1 micro after costs, IS (2021-10..2023-12) and J (2024-01..2026-10)\n\n| row | IS trades | /month | win % | PF | avg $ | total $ | max DD $ | J trades | /month | win % | PF | avg $ | total $ | max DD $ |\n|" + "---|" * 15 + "\n")
    for i in ids:
        md.append(row1(i))
    md.append("\n## Table B: Lucid-fit sizing incl. grade rule (static, full room): total $ / max DD $ / taken of signals (sized 0 = signals - taken)\n\n| row | IS 25K total | DD | taken | IS 50K total | DD | taken | J 25K total | DD | taken | J 50K total | DD | taken | J 100K total | taken | J 150K total | taken |\n|" + "---|" * 17 + "\n")
    for i in ids:
        a, b = rows[i]["IS"], rows[i]["J"]
        md.append(f"| {lab(i)} | {f0(a['fit25']['total'])} | {f0(a['fit25']['mdd'])} | {a['fit25']['n']}/{a['n']} | {f0(a['fit50']['total'])} | {f0(a['fit50']['mdd'])} | {a['fit50']['n']}/{a['n']} | "
                  f"{f0(b['fit25']['total'])} | {f0(b['fit25']['mdd'])} | {b['fit25']['n']}/{b['n']} | {f0(b['fit50']['total'])} | {f0(b['fit50']['mdd'])} | {b['fit50']['n']}/{b['n']} | "
                  f"{f0(b['fit100']['total'])} | {b['fit100']['n']}/{b['n']} | {f0(b['fit150']['total'])} | {b['fit150']['n']}/{b['n']} |\n")
    md.append("\n## Table C: Lucid Pro eval, all rules (EOD trailing MLL + lock, DLL, 40% consistency + day stop, kill distance, 1 position, size shrinks with MLL room). pass % / bust % (rolling start every day in the period)\n\n| row | IS 25K | IS 50K | IS 100K | IS 150K | J 25K | J 50K | J 100K | J 150K |\n|" + "---|" * 9 + "\n")
    for i in ids:
        cells = [f"{rows[i][pn]['ev'+str(k)]['pas']:.1f} / {rows[i][pn]['ev'+str(k)]['bust']:.1f}" for pn in ("IS", "J") for k in PLANK]
        md.append(f"| {lab(i)} | " + " | ".join(cells) + " |\n")
    md.append("\n## Table D: Pro 50K block (and 25K beside it), IS and J\n\n| row | period | plan | taken | sized 0 | median contracts | total $ | max DD $ | eval pass % | bust % | still running % | median days to pass |\n|" + "---|" * 12 + "\n")
    for i in ids:
        for pn in ("IS", "J"):
            for k in (50, 25):
                f, e = rows[i][pn][f"fit{k}"], rows[i][pn][f"ev{k}"]
                md.append(f"| {lab(i)} | {pn} | {k}K | {f['n']} | {f['zero']} | {f['med_c']} | {f0(f['total'])} | {f0(f['mdd'])} | {e['pas']:.1f} | {e['bust']:.1f} | {e['run']:.1f} | {e['med_days'] if e['med_days'] is not None else '-'} |\n")
    md.append("\n## Table E: 10 equal chunks of the 5 years (126-127 days each): trades / 1-micro $ / PF / 25K-fit $ / 50K-fit $\n\n| chunk | days |" + "".join(f" {i} |" for i in ids) + "\n|" + "---|" * (2 + len(ids)) + "\n")
    for c in range(10):
        a = rows["BASE"]["chunks"][c]
        cells = []
        for i in ids:
            _, _, s1, t25, t50 = rows[i]["chunks"][c]
            cells.append(f"{s1['n']} / {f0(s1['total'])} / {fpf(s1['pf'])} / {f0(t25)} / {f0(t50)}")
        md.append(f"| {c+1} | {a[0]}..{a[1]} | " + " | ".join(cells) + " |\n")
    md.append("\n## Table F: win % (net of cost, 1 micro) by entry half-hour, all 5 years: wins / trades\n\n| row | 09:30-10:00 | 10:00-10:30 |\n|---|---|---|\n")
    for i in ids:
        h = rows[i]["hh"]
        cell = lambda k: (f"{100*h[k][1]/h[k][0]:.1f}% ({h[k][1]}/{h[k][0]})" if k in h else "-")
        md.append(f"| {lab(i)} | {cell(0)} | {cell(1)} |\n")
    md.append("\n## Table G: episode bookkeeping (all 5 years)\n\n| row | sweep episodes | valid IFVG | retraces | A2 fail | D2 fail | timeouts | replaced | sweeps ignored (V3) | signals skipped, position open | skipped, same bar | trades |\n|" + "---|" * 12 + "\n")
    for i in ids:
        c = rows[i]["cnt"]
        ntr = rows[i]["IS"]["n"] + rows[i]["J"]["n"]
        md.append(f"| {lab(i)} | {c.get('ep_created','-')} | {c.get('ep_ifvg','-')} | {c.get('ep_retrace','-')} | {c.get('ep_a2','-')} | {c.get('ep_d2','-')} | {c.get('ep_timeout','-')} | {c.get('ep_replaced','-')} | {c.get('ep_ignored_protected','-')} | {c.get('skipped_pos','-')} | {c.get('skipped_same_bar','-')} | {ntr} |\n")
    yn = lambda x: "yes" if x else "no"
    md.append("\n## IS filter (vs BASE 10:00): more IS trades, IS PF >= 1.10, IS 1-micro $ >= base, IS 25K-fit $ >= base, IS 50K-fit $ >= base\n\n| row | more trades | PF >= 1.10 | 1-micro $ | 25K $ | 50K $ | ELIGIBLE | IS PF | IS 1-micro $ | IS 25K $ | IS 50K $ |\n|" + "---|" * 11 + "\n")
    bI = rows["BASE"]["IS"]
    md.append(f"| BASE | | | | | | | {fpf(bI['s1']['pf'])} | {f0(bI['s1']['total'])} | {f0(bI['fit25']['total'])} | {f0(bI['fit50']['total'])} |\n")
    for vid, _ in VAR:
        c, I = elig[vid], rows[vid]["IS"]
        md.append(f"| {vid} | {yn(c['more'])} | {yn(c['pf'])} | {yn(c['t1'])} | {yn(c['t25'])} | {yn(c['t50'])} | {yn(c['ok'])} | {fpf(I['s1']['pf'])} | {f0(I['s1']['total'])} | {f0(I['fit25']['total'])} | {f0(I['fit50']['total'])} |\n")
    md.append(f"\nIS pick (highest IS 25K-fit total among eligible): {pick}\n")
    md.append("\n## J check (J = 2024-01..2026-10; seen by earlier sessions) for every IS-eligible row\n\n| row | J 1-micro $ >= base | J 25K $ >= base | J 50K $ >= base | J PF > 1 | J trades >= base | 25K pass/bust within 2 pts | 50K pass/bust within 2 pts | J trades | VERDICT |\n|" + "---|" * 10 + "\n")
    verdicts = {}
    jrows = [v for v in ranked] + [r for r in ext_rows]
    for r in jrows:
        res = rows[r]
        c = jcheck(res, rows["BASE"])
        n = res["J"]["n"]
        verdicts[r] = c["ACCEPT"]
        md.append(f"| {lab(r)} | {yn(c['t1'])} | {yn(c['t25'])} | {yn(c['t50'])} | {yn(c['pf'])} | {yn(c['n'])} | {yn(c['p25'])} | {yn(c['p50'])} | {n}{' (too few to trust)' if n < 30 else ''} | {'ACCEPT' if c['ACCEPT'] else 'REJECT'} |\n")
    if not jrows:
        md.append("| (none IS-eligible) | | | | | | | | | |\n")
    if ext_rows:
        md.append("\n## Window 10:30 rows: IS filter vs BASE (10:00 engine as is) and vs BASE@1030\n\n| row | vs BASE 10:00 eligible | vs BASE@1030 eligible |\n|---|---|---|\n")
        for r, (a, b) in ext_rows.items():
            md.append(f"| {r} | {yn(a['ok'])} (more {yn(a['more'])}, PF {yn(a['pf'])}, 1m {yn(a['t1'])}, 25K {yn(a['t25'])}, 50K {yn(a['t50'])}) | {yn(b['ok'])} (more {yn(b['more'])}, PF {yn(b['pf'])}, 1m {yn(b['t1'])}, 25K {yn(b['t25'])}, 50K {yn(b['t50'])}) |\n")
    md.append(f"\nVariants tested: 3 at window 10:00 + {len(ext_rows)} at window 10:30 = {3+len(ext_rows)} (+ BASE refs).\n")
    open(os.path.join(OUT, "tables.md"), "w").write("".join(md))
    print("".join(md))
    print(f"total {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
