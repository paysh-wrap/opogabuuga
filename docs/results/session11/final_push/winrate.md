# Final push — can the MAIN trade stream itself be improved? (2026-11-10)

Scripts (this folder): `winrate_study.py` (round 1, engine = `rebuild_main_csv.py` noise_t / pm_fade with variant knobs; defaults
reproduce MAIN exactly: 1,291 trades, 50.0% win, PF 1.33, +$25,345), `round2.py` (refinements + new setups), `save_streams.py`.
Data: MNQ.v.0 1-min, 2021-11-01 → 2026-10-30, 1 micro, $1 fee + 1 tick slippage per side as in the existing scripts.
Method: parameters looked at on **2021-11..2023-12 (IS)**, judged on **2024-01..2026-10 (HO)**.
**PASS** = (win % up on both halves OR $ up on both halves) AND max drawdown not worse AND worst day not worse, on both halves.
Closed bars only: a stop move triggered by a 1-min close applies from the next bar; same-bar stop+target counts as stop.
Multi-micro variants are reported per micro (average of the legs). About 75 variants tested → expect a few chance passes.

Columns: trades · win % · PF · $ · max DD · worst day.

| idea | IS 2021-11..2023-12 | HO 2024-01..2026-10 | pass? |
|---|---|---|---|
| **BASE (MAIN)** | 564 · 48.6% · 1.30 · $9,363 · $1,538 · −$416 | 727 · 51.0% · 1.34 · $15,982 · $2,591 · −$748 | — |
| **NOISE lock: 1-min close ≥ +100 pt → stop to entry +10 pt; a locked stop-out ends NOISE for the day** | 562 · 50.0% · 1.33 · $9,905 · $1,538 · −$416 | 709 · 55.7% · 1.39 · $16,157 · $2,589 · −$748 | **PASS** (win and $ both up) |
| NOISE lock at +80 pt → +10 pt, no re-entry | 561 · 50.8% · 1.31 · $9,308 · $1,538 · −$416 | 704 · 57.0% · 1.40 · $16,091 · $2,589 · −$748 | PASS (win only; IS $ −55) |
| same locks at +5 pt (80 / 100) | 50.8% $9,169 / 50.0% $9,876, DD same | 57.0% $15,757 / 55.7% $15,812, DD $2,504 | PASS on win %, HO $ slightly lower |
| lock +100 → +10 WITH re-entry (the best IS pick, $10,212) | 565 · 50.1% · 1.34 · $10,212 · $1,538 · −$416 | 747 · 54.6% · 1.30 · $13,623 · $2,919 · −$748 | fail (HO $ and DD worse) |
| locks at +50/60/70 pt (any) | win 52–55%, worst day −$480/−$490 or DD up | win 57–62% | fail (IS worst day / DD) |
| lock +20 pt variants | DD $1,650–2,100 | — | fail |
| NOISE breakeven after +20/40/60/80 pt (re-entry) | win 32–47% | win 33–47%, $ −2,200…−4,000 | fail |
| 2 micros: 1 off at +20/40/60/80 pt, rest to BE | win 51–71%, $3,981–7,060 | win 57–76%, $10,700–11,300 | fail ($ −25…−58% per micro) |
| NOISE confirm: last 3/5/10 one-min closes beyond band | 49.4/48.8/50.8%, worst day −$499 | DD $2,790–2,808 | fail |
| NOISE checks every 30 min | 46.9% · $10,332 | 46.9% · $15,384 · DD $3,086 | fail |
| Fade band 1.5 / 2.5 / 3.0 sd | $8,551 / 8,451 / 8,425 | $14,222 / 14,827 / 12,109 | fail |
| Second fade per day | 48.8% · $8,448 · DD $1,816 | $16,453 · DD $3,105 | fail |
| Fade also after NOISE has exited (all days) | 646 · 50.5% · 1.35 · $11,627 · $1,600 · −$465 | 801 · 51.2% · 1.35 · $17,724 · $2,525 · −$842 | fail (worst day worse both halves) — near miss |
| **Fade after NOISE only if that day's closed NOISE trades net > 0** | 573 · 48.7% · 1.30 · $9,485 · $1,538 · −$416 | 737 · 51.2% · 1.35 · $16,651 · $2,591 · −$748 | PASS, but only 9 + 10 extra trades → chance-sized |
| lock +100/+10 no-re-entry + fade-after-win together | 575 · 50.3% · $10,053 · $1,538 | 737 · 55.6% · $17,098 · DD $3,088 | fail (HO DD) → do NOT stack |
| Fade: 1 of 2 micros off half-way to VWAP, rest to BE | 53.9% · $9,385 · DD $1,314 | 56.0% · $15,072 · DD $2,867 | fail (HO $ and DD) |
| Fade breakeven after +10 / +20 pt | win 37 / 41% | win 35 / 40% | fail |
| Fade window start 12:00 / 12:15 / 12:30 / 12:45 | 49.5–50.7% · $9,834–10,905 · DD $1,589–1,814 | 51.8–52.8% · $17,986–18,879 · DD $2,334–2,545 | fail on IS DD only (+$51…+$276) — near miss |
| Fade start 13:30 / 14:00, end 14:30 | win ≤ base | win ≤ base | fail |
| NEW gap fade 09:31 → flat 09:58 (gap 0.2–1.5 %, target half / full gap) | alone −$913…+$1,110 | alone −$5,614…+$664; combined DD/worst day worse | fail |
| NEW open displacement 5-min candle, 25-pt stop / 38-pt target, flat 09:59 | alone 50–54% · +$941…+$2,377 | alone 40–42% · −$204…−$1,005 | fail (edge gone held-out) |
| same, 90-minute window (overlaps NOISE, standalone only) | 46% · PF 1.20 · +$2,932 | 42% · PF 1.10 · +$966 | not combinable (1 position), too thin |

## Reading
1. **Only one change is worth proposing: the NOISE profit lock at +100 pt with no re-entry after a locked stop-out.** 5 years:
   1,271 trades, **53.2% win** (from 50.0%), PF 1.37 (1.33), +$26,062 (+$717), max DD $2,589 (same), worst day −$748 (same).
   Most of the win-rate gain is trades that used to come back to a small loss/scratch and now close about +$19 — the extra
   dollars are small. The +80 version gives 54.2% win but no extra money. Honest caveat: the variant with the best IS result
   (same lock, re-entry allowed) FAILED held-out, so the "no re-entry" part is doing the work and was one of ~30 lock variants
   tried; treat it as a modest, plausible improvement, not a proven edge. "Profit locks" in the rejected list were account/day
   level; this is a per-trade stop move (new).
2. Fade after a winning NOISE day passes the rule by 19 trades and breaks the drawdown when stacked with the lock → leave OFF.
3. Earlier fade start (12:30) adds +$1,000 IS / +$2,900 HO with better HO drawdown, but IS drawdown is $144 worse → fails the
   binding rule; candidate for forward (paper) evidence only.
4. Partial exits and breakeven stops raise the win rate a lot (up to 76%) but always cost 25–58% of the profit per micro: rejected.
5. No new setup (gap fade, opening displacement) survives held-out data.

## Streams (date, pnl_per_micro, strategy, entry_time)
- `streams/noise_lock100_plus10_no_reentry.csv` (recommended)
- `streams/noise_lock80_plus10_no_reentry.csv`
- `streams/fade_after_winning_noise.csv` (weak pass, not recommended)

Nothing here is built into the app; changing NOISE = unverified parameters (D55) → needs user approval and a noise_area.py re-run.
