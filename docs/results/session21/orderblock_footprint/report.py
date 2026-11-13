import json, os
H = os.path.dirname(os.path.abspath(__file__)); r = json.load(open(f"{H}/results.json")); p = r["pick"]
f = lambda s: f"{s['n']} / {s['win']:.1f}% / {s['pf']:.2f} / {s['per']:+.1f} / {s['net']:+,.0f} / {s['dd']:,.0f}"
L = []
L.append("# Order blocks + simulated footprint, MNQ (session 21, research only)\n")
L.append("**Footprint = OHLC-derived estimate, not real order flow.** Volume is the Databento 1-minute volume recovered from the stored VWAP "
         f"(v_k/V_k = (vwap_k - vwap_(k-1)) / (tp_k - vwap_(k-1)); ill-conditioned bars imputed by local median; imputed share MNQ {100*r['imputed']['MNQ']:.2f}%, MES {100*r['imputed']['MES']:.2f}%). "
         "Delta = volume x (2 x close-location - 1) (tick rule if h == l), exactly the app's method; CVD = running sum from 09:30. Robustness: range-as-volume and volume = 1 rows below.\n")
L.append("## 1. Answer\n")
L.append(f"**No edge.** Pick on IS only: OB on {p['tf']}-minute bars, variant {p['var']} (absorption), R {p['R']}: IS PF {p['IS']['pf']:.2f} ({p['IS']['per']:+.1f} $/trade) "
         f"but on the judge window J PF {p['J']['pf']:.2f}, {p['J']['per']:+.1f} $/trade, net {p['J']['net']:+,.0f}; it beat {r['random']['beats']}/30 random-side seeds on J (needs 27). "
         "Verdict rule (J PF >= 1.15, net > 0, beats >= 90% of seeds) fails on all three. MES check also negative. So NOISE + OB was not built. Every plain-OB / footprint-confirmed variant on J has PF < 1.0 on 5m and 1m.\n")
L.append("Eval bootstrap (10-day blocks, 600 paths, 400 sessions), pass% / bust%, size = plan size_table micros (Daily 25K has no table: 1 micro). Brake rows ignored.\n")
L.append("| Plan | micros | OB IS | OB J | NOISE IS | NOISE J |\n|---|---|---|---|---|---|")
for n, a in r["accounts"].items():
    c = lambda k: f"{a[k]['pass_']:.0f} / {a[k]['bust']:.0f}" + (f" ({a[k]['med']:.0f}d)" if a[k]['med'] else "")
    L.append(f"| {n} | {a['q']} | {c('OB_IS')} | {c('OB_J')} | {c('NOISE_IS')} | {c('NOISE_J')} |")
L.append("\n(median sessions to pass in brackets). Pro 100K and 150K match because 2/3000 and 3/4500 micros per MLL are the same ratio.\n")
L.append("## 2. The pick (selected on IS)\n")
L.append("Columns: trades / win / PF / $ per trade / net $ / max closed-trade DD $ (1 micro).\n")
L.append(f"- IS (to 2025-11-05): {f(p['IS'])}\n- J (2025-11-06..2026-10-30): {f(p['J'])}\n- MES check (same config, 1 micro): IS {f(r['mes']['IS'])}; J {f(r['mes']['J'])}\n")
L.append("Per-year (all trades):\n\n| Year | trades | win | PF | $/trade | net |\n|---|---|---|---|---|---|")
for y, s in p["per_year"].items():
    if s["n"]: L.append(f"| {y} | {s['n']} | {s['win']:.1f}% | {s['pf']:.2f} | {s['per']:+.1f} | {s['net']:+,.0f} |")
L.append(f"\nNOISE baseline (1 micro): IS {f(r['stream_stats']['NOISE_IS'])}; J {f(r['stream_stats']['NOISE_J'])}\n")
L.append("## 3. Full grid (recovered volume; only the pick was judged, the J columns are shown for completeness)\n")
L.append("| TF | Var | R | IS n | IS PF | IS $/tr | J n | J PF | J $/tr | eligible | picked |\n|---|---|---|---|---|---|---|---|---|---|---|")
for g in r["grid"]:
    if g["vm"] != "rec": continue
    pk = "PICK" if (g["tf"], g["var"], g["R"]) == (p["tf"], p["var"], p["R"]) else "not picked"
    L.append(f"| {g['tf']}m | {g['var']} | {g['R']} | {g['IS']['n']} | {g['IS']['pf']:.2f} | {g['IS']['per']:+.1f} | {g['J']['n']} | {g['J']['pf']:.2f} | {g['J']['per']:+.1f} | {'yes' if g['elig'] else 'no'} | {pk} |")
L.append("\nRobustness: the pick under other volume definitions (not used for selection)\n\n| Volume | IS n | IS PF | J n | J PF |\n|---|---|---|---|---|")
for g in r["grid"]:
    if (g["tf"], g["var"], g["R"]) == (p["tf"], p["var"], p["R"]):
        L.append(f"| {g['vm']} | {g['IS']['n']} | {g['IS']['pf']:.2f} | {g['J']['n']} | {g['J']['pf']:.2f} |")
L.append("\n(The full grid for range and volume=1 proxies is in results.json.)\n")
L.append("## 4. Random-side benchmark (pick, same entries/stops/R, 30 seeds)\n")
rd = r["random"]
L.append(f"- J: pick {rd['pick_J_per']:+.1f} $/trade; random mean {rd['mean']:+.1f}; pick beat {rd['beats']}/30 (needs >= 27).\n- IS: random mean {rd['IS_mean']:+.1f}; pick beat {rd['IS_beats']}/30 (the IS pick is mostly a win on the IS window and did not carry over).\n")
L.append("## 5. Caveats\n- Footprint is estimated from OHLC close location with VWAP-recovered volume, not aggressor-side order flow; per-day scale only.\n- RTH-only data (no overnight context); ATR carried across days.\n"
         "- J is about 245 sessions (~190 pick trades), J was seen before by the team; about 24 grid rows tested (x3 volume variants for robustness).\n- News not modelled; stop-first inside bars; V0 limit fill gets no target credit on its entry bar.\n"
         "- Accounts: bootstrap resamples only ~245 J sessions with 10-day blocks over 400 sessions; brake rows ignored; DLL/consistency per plan YAML via session15 engine (`lib._day`, `lib.eval_run`); plans read directly with PyYAML (lib.plan_rules only covers Pro).\n"
         "- One OB candidate per OB, consumed on first touch in the 09:45-15:00 window; multi-OB ties resolved by earliest entry.\n- Files: ob.py (engine), run.py, report.py, results.json, streams_pick_MNQ.csv, streams_pick_MES.csv.\n")
open(f"{H}/RESULTS.md", "w").write("\n".join(L))
