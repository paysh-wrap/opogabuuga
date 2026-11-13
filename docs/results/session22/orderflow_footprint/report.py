import json, os
H = os.path.dirname(os.path.abspath(__file__)); r = json.load(open(f"{H}/results.json"))
P = r["picks"]; pl = P["literal"]; pn = P.get("n150", pl)
f = lambda s: f"{s['n']} / {s['win']:.1f}% / {s['pf']:.2f} / {s['per']:+.1f} / {s['net']:+,.0f} / {s['dd']:,.0f}" if s["n"] else "0 / - / - / - / 0 / 0"
cfgname = lambda p: f"k {p['k']}, exit {'fixed 2R' if p['ex'] == '2R' else 'AR trail (BE+fee after +1R, then behind each closed 5m candle)'}, location {'ON' if p['loc'] else 'OFF'}, Casper {'ON' if p['cas'] else 'OFF'}, path OFF"
HDR = "path filter OFF (no Asia data)"
L = []
L.append("# Order flow (AR Model + Casper) with a simulated footprint, 5 years MNQ / MES (session 22, research only)\n")
L.append("**The footprint is an ESTIMATE, not real aggressor flow.** Volume is recovered from the stored VWAP (session 21 method, imputed share MNQ "
         f"{100 * r['imputed']['MNQ']:.2f}%, MES {100 * r['imputed']['MES']:.2f}%). Each 1-minute bar's volume is spread over its price rows (row = 0.5 pt MNQ, 0.25 pt MES), buy share = close location, "
         f"tick rule if high == low (the app's `footprint.py` method; my vectorised copy matches the app code on {r['validation']['poc_match']}/{r['validation']['n']} sampled 5m candles for POC and "
         f"{r['validation']['delta_match']}/{r['validation']['n']} for delta). The gates (`check_ar`, `check_casper`), the plan (`build_plan`) and the trail (`trail_stop`) are the app's own functions. "
         f"Every table below is {HDR} unless it says otherwise.\n")
L.append("## 1. Answer\n")
L.append(f"**No edge.** The shipped config as-is (path filter ON, location ON) makes **0 trades** on this data: the Asia range does not exist in RTH-only bars, so every candidate that survives the location gate "
         f"is skipped with `OF_PATH_UNKNOWN` ({r['as_is']['first_layer_counts'].get('OF_PATH_UNKNOWN', 0)} reach that layer, {r['as_is']['first_layer_counts'].get('OF_LOCATION', 0)} die earlier at location). "
         f"With the path filter OFF the 16-row grid has **no eligible row** (IS n >= 150 and PF > 1.05): the two location-ON rows that look best on IS have only 6 to 11 trades in 4 years (the shipped location gate "
         f"fires about once per 150 sessions), and every row with enough trades has IS PF between {min(g['IS']['pf'] for g in r['grid'] if g['IS']['n'] >= 150):.2f} and {max(g['IS']['pf'] for g in r['grid'] if g['IS']['n'] >= 150):.2f}. "
         f"The literal pre-registered pick (best score among all rows) is a 6-trade IS row, judged on 1 J trade, which means nothing. I therefore also judged the best row with IS n >= 150 "
         f"({cfgname(pn)}): IS {pn['IS']['n']} trades PF {pn['IS']['pf']:.2f} ({pn['IS']['per']:+.1f} $/trade), J {pn['J']['n']} trades PF {pn['J']['pf']:.2f} ({pn['J']['per']:+.1f} $/trade, net {pn['J']['net']:+,.0f}); "
         f"it beat {pn['random']['beats_J']}/30 random-side seeds on J (needs 27); the same config on MES loses in both windows. On the 9 plans it passes 0% on J and busts "
         f"{r['accounts']['pro_25k']['N150_J']['bust']:.0f}% on Pro 25K, against NOISE 55 / 45. **Verdict: not an edge** (no eligible pick; J PF < 1.15; random-side 1/30; MES negative). "
         "Small samples cut both ways: this does not prove real aggressor-flow order flow has no edge, only that this estimated, bar-derived version of it has none here.\n")
L.append("Deviation to flag: the rule \"if none eligible, pick the best score anyway\" selects the 6-trade row, so a second pick (best score with IS n >= 150) was added after the IS table and before any J number was computed. Both are judged below; neither passes.\n")
L.append("## 2. The pick\n")
L.append("Columns: trades / win / PF / $ per trade / net $ / max closed-trade drawdown $ (1 micro; MNQ $2.00/pt, MES $5.00/pt, $1.00 round-trip fee, 1 tick slippage on entry and on stop / flat exits; "
         "targets need a 1-tick trade-through; stop checked first inside a 1m bar). IS = 2021-10-01..2025-11-05, J = 2025-11-06..2026-10-30.\n")
for nm, p, tag in (("Pick used for the verdict: best row with IS n >= 150 (no row was eligible)", pn, "n150"), ("Literal pre-registered pick (best score, tiny sample)", pl, "literal")):
    if tag == "n150" and "n150" not in P: continue
    L.append(f"**{nm}**: {cfgname(p)}.\n")
    L.append(f"- MNQ IS: {f(p['IS'])}\n- MNQ J: {f(p['J'])}\n- MES IS (same config, no re-pick): {f(p['mes']['IS'])}\n- MES J: {f(p['mes']['J'])}\n")
    if tag == "n150":
        L.append("Per-year MNQ (all trades):\n\n| Year | trades | win | PF | $/trade | net |\n|---|---|---|---|---|---|")
        for y, s in p["per_year"].items():
            if s["n"]: L.append(f"| {y} | {s['n']} | {s['win']:.1f}% | {s['pf']:.2f} | {s['per']:+.1f} | {s['net']:+,.0f} |")
        L.append("")
L.append(f"NOISE baseline (1 micro): IS {f(r['stream_stats']['NOISE_IS'])}; J {f(r['stream_stats']['NOISE_J'])}\n")
L.append(f"## 3. Full grid ({HDR}; J columns shown for completeness, NOT used for the pick)\n")
L.append("| k | exit | location | Casper | IS n | IS PF | IS $/tr | J n | J PF | J $/tr | eligible | status |\n|---|---|---|---|---|---|---|---|---|---|---|---|")
for g in r["grid"]:
    st = "literal pick" if g is not None and (g["k"], g["ex"], g["loc"], g["cas"]) == (pl["k"], pl["ex"], pl["loc"], pl["cas"]) else ("n>=150 pick" if (g["k"], g["ex"], g["loc"], g["cas"]) == (pn["k"], pn["ex"], pn["loc"], pn["cas"]) else "not picked")
    L.append(f"| {g['k']} | {'2R' if g['ex'] == '2R' else 'trail5'} | {'ON' if g['loc'] else 'OFF'} | {'ON' if g['cas'] else 'OFF'} | {g['IS']['n']} | {g['IS']['pf']:.2f} | {g['IS']['per']:+.1f} | {g['J']['n']} | {g['J']['pf']:.2f} | {g['J']['per']:+.1f} | {'yes' if g['elig'] else 'no'} | {st} |")
L.append("\nDiagnostic only (not part of the pre-registered grid, never eligible): location measured at the absorption extreme (touch of the 0.705-0.886 zone and value side at the candle low/high) instead of the candle close. "
         "Still a handful of trades; IS PFs look better only because n is 7 to 27.\n\n| k | exit | Casper | IS n | IS PF | IS $/tr | J n | J PF |\n|---|---|---|---|---|---|---|---|")
for g in r["diag"]:
    L.append(f"| {g['k']} | {'2R' if g['ex'] == '2R' else 'trail5'} | {'ON' if g['cas'] else 'OFF'} | {g['IS']['n']} | {g['IS']['pf']:.2f} | {g['IS']['per']:+.1f} | {g['J']['n']} | {g['J']['pf']:.2f} |")
L.append("\nShipped config as-is (path ON, location ON, Casper ON, k 1.0, 2R): **0 trades**. Gate counts at the first entry bar: " + ", ".join(f"{k} {v}" for k, v in r["as_is"]["first_layer_counts"].items()) + ".\n")
L.append("## 4. Random-side benchmark (same entries / stops / R, random direction, 30 seeds)\n")
for nm, p in (("n>=150 pick", pn), ("literal pick", pl)):
    rd = p["random"]
    L.append(f"- {nm}: J pick {rd['pick_J_per']:+.1f} $/trade vs random mean {rd['mean_J']:+.1f}, beat {rd['beats_J']}/30 (needs 27). IS pick {rd['pick_IS_per']:+.1f} vs random mean {rd['mean_IS']:+.1f}, beat {rd['beats_IS']}/30.")
L.append("\nThe IS random-side mean is about -4 $/trade for the n>=150 pick, so the direction logic adds a few dollars per trade in sample, but that is not enough to turn a positive net and it vanishes on J.\n")
L.append("## 5. Nine-plan eval vs NOISE (session-21 bootstrap: 10-day blocks, 600 paths, 400 sessions, plan size_table micros, session-15 engine with the intraday MAE floor)\n")
L.append("pass% / bust% (rest = still open after 400 sessions). Plans read from the session-21 commit `87ef163` so the NOISE column reproduces session 21 exactly "
         f"(NOISE matches session 21: {r['noise_matches_s21']}; pro_25k NOISE J 55 / 45). The Pro YAMLs were changed afterwards (D138: eval consistency 40%, DLL 600); that only moves Pro numbers a point or two and is shown in the second table.\n")
c = lambda a, k: f"{a[k]['pass_']:.0f} / {a[k]['bust']:.0f}"
L.append("| Plan | micros | pick IS | pick J | NOISE IS | NOISE J |\n|---|---|---|---|---|---|")
for n, a in r["accounts"].items(): L.append(f"| {n} | {a['q']} | {c(a, 'N150_IS')} | {c(a, 'N150_J')} | {c(a, 'NOISE_IS')} | {c(a, 'NOISE_J')} |")
L.append("\n\"pick\" = the n>=150 pick. The literal pick is 0 / 0 everywhere in IS (6 trades in 4 years, no path to the target) and has 1 trade in J, so it is not shown.\n")
L.append("Pro plans with today's YAMLs (D138):\n\n| Plan | pick IS | pick J | NOISE IS | NOISE J |\n|---|---|---|---|---|")
for n, a in r["accounts_current_pro"].items(): L.append(f"| {n} | {c(a, 'N150_IS')} | {c(a, 'N150_J')} | {c(a, 'NOISE_IS')} | {c(a, 'NOISE_J')} |")
L.append("")
L.append("## 6. Footprint snapshots (ESTIMATED; 3 most recent J trades of the n>=150 pick)\n")
L.append("Volume units are the recovered relative units x 1000 (the recovery fixes volume only up to a per-day unit). Ladder = the 5 one-minute bars of the confirmation candle, built with the app's `footprint()` and summed per row (row 0.5 pt). "
         "Because each 1m bar spreads its volume evenly over its rows, identical neighbouring rows are collapsed below and stacked-imbalance counts are inflated by that assumption.\n")
for s in pn["snapshots"]:
    L.append(f"**{s['date']} {s['side']} ({s['kind']})**, confirmation candle {s['confirm_candle']}: O {s['O']} H {s['H']} L {s['L']} C {s['C']}; env {s['env']}; candle delta {s['candle_delta']:+.0f}; "
             f"CVD at entry {s['cvd_at_entry']:+.0f}; est. POC {s['est_poc']}; stacked imbalances buy {s['stacked_buy']} / sell {s['stacked_sell']}; location {'OFF' if pn['loc'] is False else s['fib']}.")
    L.append(f"Limit {s['limit']} (valid 3 min), entry bar {s['entry_bar']}, fill incl. slippage {s['fill']}, stop {s['stop']}" + (f", target {s['target']}" if s['target'] else ", AR trail (no fixed target)") + f", exit bar {s['exit_bar']}, **P&L {s['pnl']:+.1f} $ (1 micro)**.\n")
    L.append("| price row | est. bid vol | est. ask vol | delta | |\n|---|---|---|---|---|")
    lad = s["ladder"]; i = 0
    while i < len(lad):
        j = i
        while j + 1 < len(lad) and (lad[j + 1]["bid"], lad[j + 1]["ask"], lad[j + 1]["poc"]) == (lad[i]["bid"], lad[i]["ask"], lad[i]["poc"]): j += 1
        a, b = lad[i], lad[j]
        pr = f"{a['price']}" if i == j else f"{a['price']} to {b['price']} ({j - i + 1} rows)"
        L.append(f"| {pr} | {a['bid']:.2f} | {a['ask']:.2f} | {a['delta']:+.2f} | {'POC' if a['poc'] else ''} |")
        i = j + 1
    L.append("")
L.append("## 7. Caveats\n")
L.append("- The footprint is estimated from OHLC close location and VWAP-recovered volume, not aggressor-side flow. Absorption, delta flips, stacked imbalances and the candle POC are therefore functions of the bar shape only. Real delta could behave differently; this test cannot say.\n"
         "- RTH only (09:30-16:00 ET). There is no overnight / Asia data, so the PATH layer cannot run (shipped config = 0 trades, reported above) and there is no 4h structure: bias = 1h + 15m confirmed swings (k = 2 bars) carried across days, tied or missing bias = no location trade.\n"
         "- Environment, ATR(5m)/ATR(20d), ER and delta baselines use windows inside the day (>= 6 five-minute candles), so no trade before about 10:00 ET. ATR/overlap thresholds (30th / 95th pct, median) come from IS only; MES uses the MNQ-IS thresholds.\n"
         "- Location uses the candle close for the fib depth and value side (pre-registered); swing range must be 0.2 to 2.5 daily ATR(20) (from ar.py). Fixed-range profile volumes are scale-equalised per day (needed only for multi-day swings). The shipped location gate fires about once per 150 sessions on this data, so every location-ON row is a tiny sample.\n"
         "- Casper price_confirms uses the 1m candle that closed just before the fill bar (a causal reading of 'entry candle'); STACKED_IMBALANCE is not generated as a signal kind here (only absorption and delta flip), so the stacked rule is inert and Casper ON = price_confirms only.\n"
         "- Limit at the confirmation candle's POC, live for the next 3 one-minute bars (confirm time = last 1m bar of the candle, so `confirm_max_age_min` 3 passes); filled on a touch; cancelled if the bar opens through the stop; a bar that touches both limit and stop is a loss. No target credit on the entry bar. Max 3 trades a day, one at a time, entries 09:35-15:30, flat 16:00.\n"
         "- Targets fill at their price after a 1-tick trade-through (session 15/21 convention) rather than with a further tick of slippage.\n"
         f"- Sample sizes: n>=150 pick has {pn['IS']['n']} IS and only {pn['J']['n']} J trades; J (about 245 sessions) was seen before by the team; the grid is 16 rows (plus 8 diagnostic). Bootstrap resamples only about 245 J sessions.\n"
         "- Accounts: brake rows ignored; Daily 25K has no size table (1 micro); numbers are from the session-15 engine as in session 21.\n"
         "- Files: of.py (engine), run.py, report.py, results.json, streams_pick_MNQ*.csv, streams_pick_MES*.csv (the `_n150` files are the pick used for the verdict).\n")
open(f"{H}/RESULTS.md", "w").write("\n".join(L))
