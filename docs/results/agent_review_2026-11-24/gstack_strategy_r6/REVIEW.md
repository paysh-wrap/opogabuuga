# Strategy refinement review, round 6 (2026-11-24, read-only, no new backtests)

Method note: /office-hours, /plan-ceo-review, /plan-eng-review and /retro were loaded through the Skill tool, but they are interactive, state-writing workflows (questions, ~/.gstack logs, plan files). I did not run them end to end. I applied their lenses by hand to the repo's own results. /investigate is not installed (Unknown skill); the regime analysis below is my equivalent. No code changed.

## Verdicts by lens
- Office hours: NOISE is worth building on. It is the only leg that beats random-direction controls on 7.5 years (PF 1.49, 654 trades 2021-26 PF 1.52). But the edge is thinner than the headline: judge PF 1.50 falls to 1.29 without 2024 H2, and since 2025-07 PF 1.48 sits at the random p95 (1.46). Plan on PF 1.2-1.4.
- CEO review: keep NOISE fast-evaluation as main. Order Flow stays paper-only (held-out PF 0.69, 0 trades at shipped settings). The combined option is just NOISE + CANDACE, and CANDACE is a weak add-on (PF 1.22, CI 0.92-1.59, backtest engine differs from live). Do not expand scope. About 120 variants tested across rounds, zero adopted; the search is exhausted.
- Eng review: main risks are not strategy but fidelity: live CANDACE sees overnight bars the research never had; early-close days are absent from the data (11 known days, never simulated); news blackouts only partly modelled; late-day leg is blocked by NOISE on 26% of signals and is inside the random band.
- Investigate (regime): the 150K config passes 100% for most start half-years but 14% (2025 H1) for the 79% config and 38% (2025 H2) for the built config; 50K 5% in 2025 H2. Cause: pass needs a good run inside a window, and NOISE returns are lumpy (2024 H2 PF 2.98, 2025 H1 PF 0.92, Jan-2026 rolling PF 1.04). That is about 11 independent windows, so 74-79% has a roughly 55-100% range. Robustness comes from lower dependence on one regime (smaller size, more time, more accounts), not from more tuning. Fast-pass rows were picked from 100+ configs with judge inside the selection rule, so they are optimistic.
- Retro: rounds 2-5 found nothing that beats the shipped settings (lock level, stops, 30-min entries, vol sizing, regime/VIX gates, leg priority, brake and grow ladders, new third legs, late-day gates). Real wins came from audits (model_qa), not searches. Lesson: more parameter hunting is negative value; each extra try raises false-win risk.

## ONE prioritized list (12 items)

### DO NOW
1. Present pass % as ranges with the per-half-year table in the UI/brief (use sim150.boot_intervals); treat gaps under 10 pts as ties. Benefit: honest expectations, no wrong sizing. Evidence: tested (model_qa #1, round 3). Lucid risk: none. Effort: S.
2. Hard-code the CME early-close calendar (Nov 26/27, Dec 24, Dec 25) and flatten 15-30 min before the earliest stated time; disable late-day leg those days. Benefit: avoids a rule breach (flat by close). Evidence: untested in sim (data has no half days; dates are third-party). Lucid risk: high if missed. Effort: S. Verify dates on CME advisories first.
3. Keep late-day leg and CANDACE OFF (or minimum size) for real evaluations until out-of-sample evidence exists. Benefit: removes two unproven legs that lower judge pass on 100K/150K. Evidence: tested (model_qa, r5: 0 of 8 gates). Lucid risk: lowers. Effort: S.
4. Plan on PF 1.2-1.4 and budget the +$2/micro cost sensitivity (150K pass 74% to 64%). Benefit: realistic size and fee planning. Evidence: tested. Risk: none. Effort: S.
5. Use the shipped fast-pass sizes only on exact-size eval accounts; for 50K keep today's setup (no setup beat it). Benefit: avoids chasing noise. Evidence: tested. Risk: unchanged. Effort: none.
6. Add a decay monitor: flag when rolling 12-month NOISE PF stays below 1.1 for two quarters (happened once, Jan 2026). Benefit: early stop signal. Evidence: tested as observation. Risk: none. Effort: S.

### NEEDS DATA
7. Fix CANDACE fidelity: feed live logic RTH-only bars, or obtain all-hours MNQ history and rerun. Benefit: makes the leg's evidence mean something. Evidence: untested; sign unknown. Risk: medium (live differs from backtest). Effort: M. Needs overnight data.
8. Freeze one untouched window (next 6 months of paper/live) as the only valid hold-out before changing any fast-pass row. Benefit: ends the selection bias. Evidence: n/a. Risk: none. Effort: S, takes months.
9. Confirm Lucid rules from official pages (40% consistency, funded EOD drawdown, DLL fee). Third-party sources conflict. Benefit: avoids breach by wrong assumption. Evidence: untested. Risk: high if wrong. Effort: S.
10. Test early-close and news-day behavior with half-day bars or a synthetic flat-time test, plus a real news calendar instead of fixed windows. Benefit: closes the biggest unmodelled rule risk. Evidence: untested. Risk: medium. Effort: M.

### STOP DOING
11. Stop parameter and filter searches on NOISE, CANDACE and the late-day leg (lock, stop, check frequency, VIX/regime gates, grow/brake grids). About 120 tries, zero adoptions; each new try adds false-win risk. Do not chase VIX-low NOISE (judge window was 85% low-VIX).
12. Stop spending effort on Order Flow AR with 1-minute estimated delta and on tuning pass-% by 0.1-2 pts; revisit only with real tick/bid-ask data.

## Honest limits
Everything is backtest on one instrument family, 2021-26; judge window was already seen by earlier sessions, so no pristine hold-out exists. About 11 independent windows. Third-party Lucid and CME facts are unverified. Items 1-6 are low risk because they reduce exposure or add monitoring; none promises more profit.
