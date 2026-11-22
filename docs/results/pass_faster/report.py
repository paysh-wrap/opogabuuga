"""Build RESULTS.md from results.json (+ repro_baseline.json). Run: python3 report.py"""
import json, os
import analyze as A
HERE = os.path.dirname(os.path.abspath(__file__))
R = A.R; g = A.g
NAMES = {"BASE": "BASE (NOISE shipped)", "LOCK80": "LOCK80 (lock trigger 80 pt)", "N+CANDACE": "NOISE + CANDACE", "N+VWAP": "NOISE + CONTI VWAP"}
MIXES = ["BASE", "LOCK80", "N+CANDACE", "N+VWAP"]
f0 = lambda x: "-" if x is None else f"{x:.0f}"
f1 = lambda x: "-" if x is None else f"{x:.1f}"
usd = lambda x: f"{x:,.0f}"
out = []
W = out.append


def cell(r): return f"{r['pass_']:.0f} / {r['bust_all']:.0f} / {r['run']:.0f} | {f0(r['med'])} / {f0(r['p75'])} | {r['p60']:.0f}"


def main_table(meth, wins, title):
    W(f"\n### {title}\n")
    hdr = "| plan | test |" + "".join(f" {w}: pass / bust / running % | median / 75th pct days | pass within 60 d % |" for w in wins)
    W(hdr); W("|---|---|" + "---|---|---|" * len(wins))
    for k in (25, 50):
        for m in MIXES:
            W(f"| Pro {k}K | {NAMES[m]} |" + "".join(f" {cell(g(m, k, meth, w))} |" for w in wins))


# ---------------------------------------------------------------- 0 reproduction
rep = json.load(open(HERE + "/repro_baseline.json"))
yaml_rows = {"lucid_pro_25k|all": "57/43, 56d", "lucid_pro_25k|j": "40/60, 40d", "lucid_pro_50k|all": "65/34, 78d", "lucid_pro_50k|j": "52/48, 55d"}

# ---------------------------------------------------------------- verdict
def vrow(test, k, w, meth):
    v = A.verdict_cell(test, k, w, meth)
    yn = lambda b: "yes" if b else "NO"
    return v, f"| Pro {k}K | {w} {'rolling' if meth == 'roll' else 'bootstrap'} | {v['d_pass']:+.1f} | {('%+.0f' % v['d_med']) if v['d_med'] is not None else '-'} | {v['d_bust']:+.1f} | {v['d_tp']:+,.0f} / {v['d_t1']:+,.0f} | {yn(v['faster_or_more'])} | {yn(v['bust_ok'])} | {yn(v['profit_ok'])} | **{'PASS' if v['ok'] else 'FAIL'}** |"


W("# Pass faster: three offline tests vs the shipped NOISE eval config (Pro 25K and 50K, EOD, all Lucid rules on)\n")
W("Research only. No app code, config or frontend changed; nothing committed. Scripts and raw numbers are in this folder.\n")
W("## Plain-English summary\n")
verd = {}
for test in A.TESTS:
    verd[test] = [A.verdict_cell(test, k, w, "roll")["ok"] for k in (25, 50) for w in ("JUDGE", "ALL")]
W("**Baseline reproduced first.** The session-21 realistic account simulator, run unchanged on the same stream, gives Pro 25K 57/43 (56 days) over 5 years and 40/60 (40 days) over the last 12 months, "
  "and Pro 50K 65/34 (78 days) and 52/48 (55 days): an exact match to `config/eval_odds.yaml` (see section 1). The simulator I used for the tests gives the identical numbers when only NOISE is on.\n")
W("**Answer: none of the three is worth building.**\n")
W("- **LOCK80 (lock trigger 80 pt instead of 100): fails the rule, but narrowly and mostly by noise.** On the held-out window it looks good on both sizes "
  f"(25K pass {g('LOCK80',25,'roll','JUDGE')['pass_']:.0f}% vs {g('BASE',25,'roll','JUDGE')['pass_']:.0f}%, 50K {g('LOCK80',50,'roll','JUDGE')['pass_']:.0f}% vs {g('BASE',50,'roll','JUDGE')['pass_']:.0f}%, bust lower, profit higher), "
  f"and 50K also over 5 years. But it is NOT faster (median days to pass 2-4 days longer on the judge window), it does not help in the pick window (2021-10..2023-12: pass 25K {g('LOCK80',25,'boot','PICK')['pass_']:.0f}% vs {g('BASE',25,'boot','PICK')['pass_']:.0f}%, "
  f"50K {g('LOCK80',50,'boot','PICK')['pass_']:.0f}% vs {g('BASE',50,'boot','PICK')['pass_']:.0f}%; static profit lower on 25K), and on Pro 25K over 5 years with rolling starts it is worse (pass {g('LOCK80',25,'roll','ALL')['pass_']:.0f}% vs {g('BASE',25,'roll','ALL')['pass_']:.0f}%, bust+stuck {g('LOCK80',25,'roll','ALL')['bust_all']:.0f}% vs {g('BASE',25,'roll','ALL')['bust_all']:.0f}%, "
  "a +4.6 pt bust rise, over the 2-pt limit). The paired by-quarter comparison is inside the noise (25K -3.8 +/- 5.0 pts, 50K +2.8 +/- 2.0). It is the same pattern session 19 saw (good in the last 12 months only). Verdict: FAIL on the stated rule (1 of 4 required cells fails) and not a speed-up.")
W("- **NOISE + CANDACE: fails.** It does make passing faster when it passes (median days 59 vs 74 over 5 years on 25K, 78 vs 92 on 50K, 67 vs 83 on the judge 50K), but fewer accounts pass "
  f"(5-year rolling: 25K {g('N+CANDACE',25,'roll','ALL')['pass_']:.0f}% vs {g('BASE',25,'roll','ALL')['pass_']:.0f}%, 50K {g('N+CANDACE',50,'roll','ALL')['pass_']:.0f}% vs {g('BASE',50,'roll','ALL')['pass_']:.0f}%; judge 50K {g('N+CANDACE',50,'roll','JUDGE')['pass_']:.0f}% vs {g('BASE',50,'roll','JUDGE')['pass_']:.0f}%) "
  "and more accounts end stuck (bust +2 to +13 pts), and on Pro 25K the plan-sized profit in the judge window is lower (-$397). On 25K CANDACE is sized to 0 micros for about 70% of its signals, so it adds almost nothing there. "
  "(For the accounts that do pass, CANDACE is slightly quicker: share of starts passing within 60 days 25% vs 23% on 25K and 25% vs 20% on 50K over 5 years, but that is within noise and does not offset the lost passes.) "
  "The 25K 5-year drop comes from one cluster (accounts started mid-2023 that were still running in Jan 2024), so treat it as fragile, but nothing in the numbers supports building it.")
W("- **NOISE + CONTI VWAP: fails badly.** CONTI VWAP fires about 3.7 signals a day with an essentially flat edge (+$254 per micro over 5 years on 4,745 trades), 25 pt stops and heavy cost. "
  f"On the same account it grinds the MLL room away: pass {g('N+VWAP',25,'roll','ALL')['pass_']:.0f}% (25K) and {g('N+VWAP',50,'roll','ALL')['pass_']:.0f}% (50K) over 5 years vs {g('BASE',25,'roll','ALL')['pass_']:.0f}% / {g('BASE',50,'roll','ALL')['pass_']:.0f}%, "
  "about 90% of accounts end stuck, and plan-sized profit falls by $6,900 (25K) and $13,700 (50K). The shorter median days (13-15) is survivorship: only the 9% that pass quickly are counted.\n")
W("In the table below `pass / bust / running` are % of rolling starts; bust includes accounts stuck below the trading room (same definition as `eval_odds.yaml`; there are 0 outright kill-switch busts in any row). "
  "Days are trading sessions. `pass within 60 d` is the share of ALL starts that pass inside 60 sessions: it avoids the survivorship effect of a median taken only over the accounts that pass.\n")
W("### Headline table (rolling starts, plan sizing: 25K = 1 micro, 50K = 2 micros with the brake)\n")
W("| plan | test | 5y: pass / bust / running % | 5y median days | judge 2024-26: pass / bust / running % | judge median days | 5y plan-sized profit $ | judge plan-sized profit $ | rule met in (judge, 5y) windows |")
W("|---|---|---|---|---|---|---|---|---|")
for k in (25, 50):
    for m in MIXES:
        a, j = g(m, k, "roll", "ALL"), g(m, k, "roll", "JUDGE"); sa, sj = g(m, k, "static", "ALL"), g(m, k, "static", "JUDGE")
        ver = "baseline" if m == "BASE" else f"{sum(A.verdict_cell(m, k, w, 'roll')['ok'] for w in ('JUDGE', 'ALL'))} of 2"
        W(f"| Pro {k}K | {NAMES[m]} | {a['pass_']:.0f} / {a['bust_all']:.0f} / {a['run']:.0f} | {f0(a['med'])} | {j['pass_']:.0f} / {j['bust_all']:.0f} / {j['run']:.0f} | {f0(j['med'])} | {usd(sa['tp'])} | {usd(sj['tp'])} | {ver} |")
W("\n**Verdict rule (all four cells must pass: 25K and 50K, judge window and 5 years):** median days lower OR pass % higher; bust+stuck not higher by more than 2 pts; total profit (plan-sized and 1-micro) not lower. "
  "Overall verdict: no test passes (the 'rule met' column must read 2 of 2 on BOTH plans; LOCK80 reads 1 of 2 on 25K and 2 of 2 on 50K, i.e. 3 of 4 cells). See section 3 for each cell. Caveat on the rule itself: the median is taken only over accounts that pass, so a test that makes many accounts fail can show a lower median by survivorship (CONTI VWAP, partly CANDACE); I mark the rule as met only literally in those cases.\n")
W("**Multiple testing and reuse of data.** Three tests plus two sub-views, on one 5-year MNQ sample; 2024-26 was seen by many earlier sessions (including the LOCK80 idea itself, session 19 item 6a, which was found on the last 12 months). "
  "The rolling starts overlap heavily (about 20 independent evaluation lengths in 5 years), so a 2-4 point difference is not distinguishable from noise. "
  "Nothing here justifies building anything; LOCK80 is the only one that could be re-checked on genuinely new data.\n")

# ---------------------------------------------------------------- sections
W("\n---\n\n## 1. Baseline reproduction (stop condition: passed)\n")
W("Stream: session-20 `streams_BASE.csv` (NOISE, preset C lock +100 pt -> stop entry+10, Mondays off, no fade, 654 trades 2021-10-22..2026-10-30). I regenerated it from the engine-mirror generator (`session20/noise3.gen()`) on the shared days.pkl: **654/654 identical** (net $19,293). "
  "Simulator: session-21 `sim2.py` unchanged (paths patched only), session-21 bootstrap protocol (10-day blocks, uniform start, 600 paths x 400 sessions, seed 7, plan size tables, D57 shrink, kill distance, room check, brake, STUCK test with gmin $112).\n")
W("| row | `eval_odds.yaml` (pass/bust, median days) | reproduced |\n|---|---|---|")
for key, lab in (("lucid_pro_25k|all", "Pro 25K, 5 years"), ("lucid_pro_25k|j", "Pro 25K, last 12 months"), ("lucid_pro_50k|all", "Pro 50K, 5 years"), ("lucid_pro_50k|j", "Pro 50K, last 12 months")):
    r = rep[key]
    W(f"| {lab} | {yaml_rows[key]} | {r['pass']:.1f}/{r['bust']:.1f}, {r['days']:.1f}d |")
W("\nExact match (within 0.5 pt, well inside +/-2). The test simulator `pf_sim.py` (NOISE + extra strategies on one account) was also run in NOISE-only mode and matches sim2 to the last digit on all 6 era x plan rows (`validate.py`); the float re-implementation of the CANDACE / VWAP Lucid fit matches the app's Decimal `lucid_fit` functions on 20,000 random inputs (0 mismatches).\n")

W("## 2. Method\n")
W("""- **Account (all tests, 25K and 50K, EOD):** balance, trailing EOD MLL with lock (25K lock at 26,100 -> 25,100), DLL incl. LucidScale (60% of peak EOD profit once locked), 40% consistency at pass + 38% day stop (a trade is capped at the day stop and the day ends), kill distance + room check before every trade, D57 shrink for NOISE, the plan's size table and brake for NOISE, STUCK = NOISE can no longer be sized (counts as bust, as in `eval_odds.yaml`), max one position per account, no hedging (all MNQ, one position), flat by close (streams are flat by 16:00).
- **Streams:** NOISE base and LOCK80 from `noise3.gen()` (LOCK80 = `lock=(80, 10)`: trigger 80 pt, stop to entry+10; 647 trades, net $19,634 vs 654 / $19,293). CANDACE = engine `candace_ict.replay_day` with D154 defaults (keep_all_sweeps ON, 09:30-10:00), 310 signals (304 from 2021-10-21), through the existing study harness (`ctm_lib.engine_trades`, 3 prior days of history). CONTI VWAP = engine `conti_vwap.replay_day`, defaults, volume recovered from the stored VWAP as in session 21: 4,745 signals.
- **Sharing one account:** all signals of both strategies are merged by entry minute. A signal is skipped if its entry minute is at or before the exit minute of the position the account holds (NOISE's own same-bar flip is allowed as it is its own rule). A signal that sizes to 0 contracts does not block anything. NOISE exits are intrabar or at the open of the exit bar, so NOISE exit minute = exit bar + 0.5 (slightly conservative).
- **Sizing:** NOISE by its plan size table (25K: 1, 50K: 2 with brake) and the room/shrink logic of session 21. CANDACE and VWAP by the controller's Lucid fit: `trade_risk_usd` (risk % of drawdown, DLL left x use %, MLL room less kill distance, per-trade cap, day stop, divided by losses/session) then `contracts_for` (stop $ + fee + slippage), capped at max micros; CANDACE then the grade rule (A+ full, B and C halved or less, `grade_contracts`). DLL room for fit strategies is the D18 reading (`dll_remaining`, drop from the day's best P&L); NOISE keeps the session-21 reading.
- **Rolling starts:** a start on every trading day of the window; each run follows the real days from that start to the end of the window (5 years: 2021-10-21..2026-10-30; pick: ..2023-12-31; judge: 2024-01-01..2026-10-30) and ends at pass, stuck/bust, or the window end (= still running). Starts late in a window are censored (more `running`), the same for every test. Pick-window rolling rows use only pick-window days. Days to pass = trading sessions from the start day (no-trade days count).
- **Bootstrap:** the session-21 protocol on the same windows (cross-check; includes `L12` = last 12 months to compare with `eval_odds.yaml`).
- **Static (profit, trades/week, drawdown, skips):** a fresh-account replay with no balance dependence: NOISE at its table size (no brake or shrink), CANDACE/VWAP at the full-room Lucid fit, one position at a time. 1-micro = every signal at 1 micro, one position at a time. `worst DD` = largest peak-to-trough of the cumulative P&L of the merged stream.
- **Stuck rule for mixes:** primary = the baseline definition (account stuck as soon as NOISE cannot be sized). Sensitivity = not stuck while CANDACE/VWAP could still size 1 micro (section 6): it moves accounts from `bust` to `running`, it creates no passes of note.
""")

W("## 3. Verdict cell by cell (rolling starts, then bootstrap in the same format)\n")
W("Differences are test minus BASE. Profit = static plan-sized / static 1-micro total over the window.\n")
W("| test | plan | window | d pass (pts) | d median days | d bust+stuck (pts) | d profit $ (plan / 1-micro) | faster or more pass | bust ok (<= +2) | profit not lower | cell |\n|---|---|---|---|---|---|---|---|---|---|---|")
for test in A.TESTS:
    for k in (25, 50):
        for w in ("JUDGE", "ALL"):
            for meth in ("roll", "boot"):
                v, line = vrow(test, k, w, meth)
                W(f"| {NAMES[test]} " + line)
W("\nThe rolling rows are the verdict rows; the bootstrap rows are a cross-check. Where they disagree (LOCK80 Pro 25K 5 years: rolling bust +4.6, bootstrap bust -4.2) the result is within noise and it shows the LOCK80 25K conclusion is not robust either way.\n")
W("**Paired by start quarter (5-year rolling, pass % of the test minus BASE, 21 quarters):**\n")
W("| test | plan | mean diff (pts) | std error | quarters better / worse / equal (+/-0.5) |\n|---|---|---|---|---|")
for test in A.TESTS:
    for k in (25, 50):
        q = A.quarterly(test, k)
        W(f"| {NAMES[test]} | Pro {k}K | {q[2]:+.1f} | {q[3]:.1f} | {q[4]} / {q[5]} / {q[6]} |")
W("\nCANDACE on Pro 25K: 114 of the 1,252 starts pass in BASE but are stuck with CANDACE, almost all starting 2023-06..2023-11; they are the long-running accounts (250+ sessions) that sit near the floor, and an ordinary CANDACE/NOISE difference around 2024-01 tips them. One cluster, not 114 independent events.\n")

main_table("roll", ("ALL", "JUDGE", "PICK"), "4. Full results, rolling starts (5 years / judge 2024-01..2026-10 / pick 2021-10..2023-12)")
W("\nPick-window rolling runs stop at 2023-12-31, so late starts are cut off and `running` is large; compare rows within the column only.\n")
main_table("boot", ("ALL", "JUDGE", "PICK", "L12"), "4b. Same, session-21 bootstrap protocol (cross-check; L12 = last 12 months, comparable with eval_odds.yaml)")

W("\n## 5. Profit, trades per week, worst drawdown, skipped signals (static replay)\n")
W("`1-micro` = all signals at 1 micro; `plan-sized` = NOISE at its table size, CANDACE/VWAP at the Lucid fit. trades/week = trades taken per 5 trading days. Skips = signals not taken because the OTHER strategy held a sized position (CANDACE/VWAP signals that size to 0 contracts block nothing).\n")
W("| plan | test | window | 1-micro $ | plan-sized $ | trades/week | worst DD 1-micro / plan-sized $ | NOISE taken / signals | other taken / signals | NOISE skipped (other open) | other skipped (NOISE open) | other skipped (own previous trade, VWAP same-bar rule) | other sized to 0 |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for k in (25, 50):
    for w in ("ALL", "JUDGE", "PICK"):
        for m in MIXES:
            s = g(m, k, "static", w)
            tk = s["taken"]; sg = s["sig"]; kind = 1 if m == "N+CANDACE" else 2 if m == "N+VWAP" else None
            tw = sum(tk.values()) / (s["ndays"] / 5)
            ot = f"{tk[str(kind)]} / {sg[str(kind)]}" if kind else "-"
            osk = s["skip_other"][str(kind)] if kind else "-"
            oown = (s["skip_open"][str(kind)] - s["skip_other"][str(kind)]) if kind else "-"
            o0 = s["size0"][str(kind)] if kind else "-"
            W(f"| Pro {k}K | {NAMES[m]} | {w} | {usd(s['t1'])} | {usd(s['tp'])} | {tw:.1f} | {usd(s['dd1'])} / {usd(s['ddp'])} | {tk['0']} / {sg['0']} | {ot} | {s['skip_other']['0']} | {osk} | {oown} | {o0} |")
W("\nReading the skips: NOISE loses 5-16 of 654 signals to CANDACE over 5 years (<= 2.5%) and CANDACE loses 1; against CONTI VWAP NOISE loses 84 of 654 (13%) because VWAP is in a position almost all the time (VWAP: 2,738 trades taken on 25K; 1,956 of its 4,694 signals skipped, 1,875 of them its own same-bar reversals under the D139 rule and 81 because NOISE was open).\n")

W("## 6. Sensitivity: STUCK rule that lets CANDACE / VWAP keep an account alive (rolling, pass / bust+stuck / running %, median days)\n")
W("| plan | test | window | primary rule | sensitivity rule |\n|---|---|---|---|---|")
for k in (25, 50):
    for m in ("N+CANDACE", "N+VWAP"):
        for w in ("ALL", "JUDGE"):
            a = g(m, k, "roll", w); b = g(m, k, "rollmix", w)
            W(f"| Pro {k}K | {NAMES[m]} | {w} | {a['pass_']:.0f} / {a['bust_all']:.0f} / {a['run']:.0f}, {f0(a['med'])}d | {b['pass_']:.0f} / {b['bust_all']:.0f} / {b['run']:.0f}, {f0(b['med'])}d |")
W("\nThe sensitivity rule turns stuck accounts into zombie 'running' accounts that cannot realistically finish; pass % barely moves, so the verdict does not depend on it.\n")

W("## 7. Caveats\n")
W("""- **Streams are independent runs of each engine, merged afterwards.** When a signal is skipped because the other strategy is in a position, the skipped strategy's own state machine (NOISE signal counter of 3 per day, CANDACE one-trade-per-setup, VWAP position flip) is not re-run. A faithful rerun would let NOISE re-enter at its next hourly check and CANDACE re-arm its setup; the effect is small (5-16 NOISE signals and 1 CANDACE signal over 5 years) but not zero. For VWAP it is large, but VWAP loses by a wide margin anyway.
- **Strategy-internal day limits** (CANDACE max losses per day, VWAP losses per day) count only that strategy's own trades.
- **Shared-day limits** (DLL, 38% consistency day stop, MLL room) are shared and are applied to every trade; a trade is capped at the day stop (flatten) as in session 21.
- **Pro 25K sizing makes CANDACE almost inert** (only 94 of 304 signals get >= 1 micro after the grade rule; static plan-sized +$253 over 5 years).
- **Median days to pass is conditional on passing** and differs by protocol (rolling real days vs 10-day-block bootstrap; rolling 5-year medians are longer than the bootstrap ones). Compare within a protocol.
- **No outright busts occur in any run**: every non-pass is STUCK (room too small to size NOISE) or still running, exactly as in `eval_odds.yaml`. The 2-pt bust rule therefore applies to stuck + bust.
- Rolling starts are overlapping and heavily clustered; no confidence interval beyond the by-quarter pairing in section 3 is given.
""")
W("## 8. Files\n")
W("""- `repro_baseline.py` / `repro_baseline.json`: step 0 (session-21 sim2, unchanged, exact reproduction).
- `gen_streams.py`: builds `streams_noise_base.csv`, `streams_noise_lock80.csv`, `streams_candace.csv`, `streams_vwap.csv` (run from `backend/` with `PYTHONPATH=.`).
- `pf_sim.py`: account simulator for NOISE + CANDACE / VWAP; `validate.py`: sim2 equality + fit-sizing equality; `run_all.py`: runs everything -> `results.json`; `analyze.py` + `report.py`: verdict checks and this file; `show.py`: quick print.
""")
open(HERE + "/RESULTS.md", "w").write("\n".join(out) + "\n")
print("written", len(out))
