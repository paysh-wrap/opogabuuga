# Session 15 - best strategy for Lucid Pro accounts (research only, nothing in the app changed)

## The recommendation in one paragraph

**Keep NOISE on MNQ, add the profit lock, switch the afternoon fade off, and trade smaller. Best plan: Lucid Pro 150K at 3 micros, dropping to 1 micro
whenever the cushion above the loss limit is under $2,250.** On the held-out years (2024-01 .. 2026-10) that setup passes the evaluation **77%** of the
time, busts the evaluation **18%**, busts a funded account in its first year **11%**, and pays about **$79 per 2 weeks per account ($397 for 5
accounts)** in the first funded year. Today's setup (NOISE alone at the live sizes) on the same years: pass 48%, eval bust 52%, funded bust 46%, $52 per
2 weeks. Nothing outside the NOISE family survived the test - 14 other well-known ideas on MNQ, MES and MGC all failed.

**What could not be reached - said plainly:**
- **A 60-70% win rate is not reachable with a real edge.** The best honest win rate is **48% (pick period) / 52% (held-out)**. Every idea that showed
  55-61% wins either lost money or needed targets below 1.5R (which break your R:R rule) - and those lost money too.
- **A 60-70% eval pass rate IS reachable on 50K, 100K and 150K (77-78% held-out), but only by trading small, which is slow:** the typical evaluation
  takes about **7 to 9 months** of trading days, and first-year funded income is small.
- **Pro 25K cannot meet the limits at all.** One micro is already too big for its $1,000 loss limit (4 stop-outs): best case 56% pass / 44% eval bust
  / 62% funded bust. Do not buy 25K accounts for this strategy.

## Table per Pro plan (recommended setup = NOISE + profit lock on MNQ, no fade)

Win rate is the same on every plan (same trades): **48.0% pick period (IS) / 52.1% held-out (HO)**, 150-160 trades a year, profit factor 1.50 / 1.38.
IS = 2021-11..2023-12 (the easy period), HO = 2024-01..2026-10 (the hard one - plan on HO).

| plan | size | eval pass IS / HO | eval bust IS / HO | typical time to pass (HO) | funded bust yr 1 IS / HO | income per 2 weeks, 1 account IS / HO | 5 accounts IS / HO | meets your limits? |
|---|---|---|---|---|---|---|---|---|
| **Pro 25K** | 1 micro | 76% / 56% | 24% / 44% | 38 sessions | 34% / 62% | $76 / $29 | $380 / $143 | **NO** (closest possible) |
| **Pro 50K** | 1 micro | 96% / 77% | 4% / 23% | 143 sessions (~7 months) | 3% / 23% | $72 / $46 | $362 / $230 | yes |
| **Pro 100K** | 2 micros, 1 while the cushion is under $2,100 | 97% / 78% | 2% / 19% | 197 sessions (~9 months) | 1% / 14% | $126 / $61 | $629 / $307 | yes |
| **Pro 150K** (best) | 3 micros, 1 while the cushion is under $2,250 | 96% / 77% | 1% / 18% | 182 sessions (~9 months) | 1% / 11% | $174 / $79 | $870 / $397 | yes |

For comparison, **today's setup** (NOISE alone, live size table), held-out: 25K pass 47% / eval bust 53% / funded bust 72% / $16; 50K 51% / 49% / 65%
/ $34; 100K 57% / 43% / 48% / $40; 150K 48% / 52% / 46% / $52. The recommendation roughly halves (or better) every bust rate and pays more.

First funded year in dollars, per account, held-out: 50K mean $1,198 (half of accounts get $704 or less, 62% get at least one payout); 100K mean $1,595
(median $908, 59%); 150K mean $2,065 (median $1,017, 56%). Pick-period figures are about double ($1,881 / $3,271 / $4,524).
**Five accounts take the same trades, so they pay together and bust together** - "5 accounts" is simply 5 x one account, not five independent chances.

## What the profit lock is (the only strategy change)
NOISE unchanged (hourly checks, enter when price closes outside the 14-day noise band, exit when the hourly close crosses back through the band/VWAP,
flat 16:00, $250 emergency stop per micro, max 3 a day). Added: **once a trade is 100 points in profit, the stop moves to entry + 10 points; if that
locked stop is hit, NOISE is done for the day.** This is proposal D75-P1 from session 11 - it was not re-tuned here.
- It is a stop move, not a profit target, so no target below 1.5R is introduced. But be aware: the average winner shrinks. Held-out average win /
  average loss is 1.27 with the lock (1.65 without); the win rate rises 44% -> 52% and total profit is the same ($10,259 vs $10,188).
- Why it matters for prop accounts: same profit with much smaller swings (per-trade swing $289 -> $233 held-out), and account survival depends on
  profit relative to swings.
- Not a knife-edge: lock at +75, +100 or +150 points, locking 0, 10 or 25 points - every neighbour beats plain NOISE in both periods (table below).

| lock setting | IS win / PF / profit / edge ratio | HO win / PF / profit / edge ratio |
|---|---|---|
| none (plain NOISE) | 45.4% / 1.45 / $8,742 / 1.49 | 44.2% / 1.31 / $10,188 / 0.55 |
| +75 pt -> entry +10 pt | 50.3% / 1.47 / $8,356 / 1.56 | 56.5% / 1.44 / $10,586 / 0.98 |
| +100 pt -> entry +0 pt | 44.2% / 1.49 / $9,022 / 1.58 | 40.6% / 1.36 / $9,768 / 0.85 |
| **+100 pt -> entry +10 pt (used)** | 48.0% / 1.50 / $9,260 / 1.63 | 52.1% / 1.38 / $10,259 / 0.89 |
| +100 pt -> entry +25 pt | 48.0% / 1.46 / $8,462 / 1.54 | 52.0% / 1.35 / $9,516 / 0.88 |
| +150 pt -> entry +10 pt | 45.7% / 1.47 / $8,963 / 1.53 | 47.4% / 1.28 / $8,520 / 0.70 |
| +200 pt -> entry +10 pt | 45.7% / 1.47 / $8,963 / 1.53 | 45.6% / 1.34 / $11,107 / 0.60 |

"Edge ratio" = 2 x average profit per trade / (swing per trade)^2, x 1000. It is the number that decides how likely an account is to reach its target
before its loss limit at a given size. Higher is better.

## How the test was run (the strict rules)
- **Causal.** A signal uses only bars that have closed; entry is the next bar's open. No "NOISE never traded today" style rule anywhere.
- **Real costs.** 1 tick of slippage on every market entry, exit and stop; limit targets need price to trade 1 tick through; fees $1.00 per micro
  round trip (MNQ, MES), $1.50 (MGC).
- **Pick on 2021-11..2023-12, judge on 2024-01..2026-10.** A candidate had to show profit factor >= 1.15 on >= 100 trades in the pick period before
  its held-out result counted. Parameters were fixed from the idea's usual description before any result was seen - no grids.
- **Data.** Databento 1-minute bars, MNQ.v.0, MES.v.0, MGC.v.0 (volume roll), 2021-10 .. 2026-10 (raw files are not committed; `build_raw.py`
  documents the download).
- **Account rules.** Each Pro plan's own rules from `config/rules/lucid_pro_*.yaml`: EOD trailing loss limit and its lock, daily loss limit, profit
  target, 40% payout consistency, payout caps / buffer / 90% split, payout every 10 sessions. The engine (`lib.py`) is the app's projection engine
  (`backend/app/backtest/income_projection.py`): with the extra check switched off it reproduces `project()` to the cent (25K: bust 41.1%, year mean
  $1,065.95 in both). The extra check makes it stricter: an account also dies if a trade's worst open loss touches the loss limit intraday.
- **"Bust" means the account is dead.** No freeze / kill-distance rule is used to hide busts (the previous agent's grid showed "0% bust" set-ups
  that were really 50-68% frozen accounts - those are not used).
- **Two estimates.** "Bootstrap" (main number): 1,000 paths built from 10-session blocks of the era's real days; evaluations run until they pass or
  bust (up to 750 sessions), funded accounts for 260 sessions. "History": rolling real start dates (every 2nd session), evaluation cut at 250 sessions.
  History has only 2-3 independent windows per era, so it is noisy; both are shown below and a set-up had to be under 35% on both.

## What was tested and failed (21 ideas besides plain NOISE, 45 market tests)
Only the NOISE family on MNQ passed the pick period AND the held-out period. Dollar figures are per 1 micro, net of costs.

| candidate | market | target R:R | IS trades / win / PF / profit | HO trades / win / PF / profit | verdict |
|---|---|---|---|---|---|
| N0 NOISE baseline | MNQ | trailing exit | 357 / 45.4% / 1.45 / $8,742 | 446 / 44.2% / 1.31 / $10,188 | passes IS and HO |
| **N1 NOISE + profit lock** | MNQ | trailing exit | 354 / 48.0% / 1.50 / $9,260 | 424 / 52.1% / 1.38 / $10,259 | **passes IS and HO - best** |
| N6 NOISE with 30-minute checks | MNQ | trailing exit | 470 / 43.4% / 1.40 / $8,989 | 580 / 40.3% / 1.27 / $10,262 | passes, but worse accounts than N0 |
| N7 NOISE 30-minute checks + profit lock | MNQ | trailing exit | 461 / 45.6% / 1.43 / $9,218 | 540 / 47.0% / 1.29 / $8,942 | passes, worse than N1 |
| N4 NOISE rules unchanged on MES | MES | trailing exit | 377 / 44.0% / 1.17 / $2,460 | 478 / 40.2% / 0.81 / -$4,186 | passes IS, FAILS held-out |
| N5 NOISE rules unchanged on MGC | MGC | trailing exit | 369 / 41.2% / 0.93 / -$533 | 436 / 38.5% / 1.17 / $3,414 | fails IS |
| V1 VWAP reversion with trend filter, 1.5R | MNQ / MES / MGC | 1.5 | 37.4% 0.93 / 31.2% 0.66 / 36.6% 0.74 | 37.8% 0.96 / 35.2% 0.85 / 45.9% 1.15 | fails IS (all three) |
| O1 Opening-range failure fade, 1.5R | MNQ / MES / MGC | 1.5 | 43.3% 1.10 / 37.1% 0.90 / 35.0% 0.75 | 42.1% 1.02 / 39.6% 0.92 / 36.9% 0.85 | fails IS (all three) |
| O2 Opening-range failure fade, target = range midpoint | MNQ / MES / MGC | varies | 48.2% 1.22 / 44.5% 0.89 / 46.9% 0.70 | 46.4% 1.02 / 48.5% 0.82 / 47.3% 0.80 | MNQ passes IS, FAILS held-out |
| O3 5-minute opening-range breakout, flat 15:55 | MNQ / MES / MGC | trailing exit | 19.7% 1.02 / 18.8% 1.01 / 19.0% 0.90 | 25.2% 1.19 / 18.5% 0.81 / 18.5% 0.88 | fails IS (all three) |
| G1 Overnight gap fill, 1.5R | MNQ / MES / MGC | 1.5 | 42.8% 1.18 / 37.5% 0.78 / 40.7% 0.82 | 42.1% 0.85 / 42.4% 0.92 / 38.3% 0.85 | MNQ passes IS, FAILS held-out (-$5,236) |
| M1 Gold overnight-VWAP reversion at the NY open, 1.5R | MGC | 1.5 | 32 trades / 28.1% / 0.40 | 44 / 38.6% / 0.54 | fails IS |
| X1 Prior-day high/low sweep-and-reclaim fade, 1.5R | MNQ / MES / MGC | 1.5 | 41.0% 0.99 / 36.5% 0.83 / 33.5% 0.74 | 40.1% 0.87 / 38.3% 0.82 / 35.1% 0.97 | fails IS (all three) |
| X2 Pre-market range sweep-and-reclaim fade, 1.5R | MNQ / MES | 1.5 | 39.1% 0.89 / 34.8% 0.74 | 38.5% 0.93 / 38.1% 1.02 | fails IS |
| X3 Gap-and-go continuation, 1.5R | MNQ / MES / MGC | 1.5 | 50.0% 1.43 (74 trades) / 43.5% 1.10 / 38.3% 0.78 | 44.2% 1.10 / 39.9% 0.97 / 40.1% 0.96 | MNQ too few trades, fades held-out |
| X4 VWAP trend-day pullback, 1.5R | MNQ / MES / MGC | 1.5 | 37.8% 0.84 / 34.7% 0.71 / 42.2% 0.79 | 39.8% 0.97 / 39.8% 0.79 / 40.9% 0.84 | fails IS (all three) |
| X5 NR7 narrow-day opening-range breakout, 2R | MNQ / MES / MGC | 2.0 | 18 trades 0.92 / 51 trades 1.22 / 52 trades 0.56 | 44 trades 2.19 / 100 trades 1.14 / 64 trades 1.05 | too few trades to trust (7-35 a year) |
| Afternoon VWAP fade (the current PM fade) | MNQ | to VWAP | PF 0.85, -$2,177 | PF 1.09, +$1,744 | no edge causally (session 14) - switch OFF |

**Separate table - ideas whose target is below 1.5R (they VIOLATE your R:R >= 1.5 rule; shown only so you can see the higher win rates do not help):**

| candidate | market | target R:R | IS win / PF / profit | HO win / PF / profit | verdict |
|---|---|---|---|---|---|
| N2 NOISE + half off at +1R, then breakeven | MNQ | 1.0 **violates** | 46.8% / 1.43 / $8,112 | 49.0% / 1.22 / $6,967 | profit -32% held-out; accounts worse than N1 |
| N3 NOISE + half off at +0.5R, then breakeven | MNQ | 0.5 **violates** | 54.1% / 1.35 / $6,216 | 57.8% / 1.17 / $4,895 | highest win rate with an edge, but half the profit; accounts worse |
| V2 VWAP reversion, stop 1.5x the target | MNQ / MES / MGC | 0.67 **violates** | 58.8% 0.97 / 48.4% 0.62 / 51.3% 0.72 | 58.7% 1.02 / 54.0% 0.81 / 61.4% 1.22 | fails IS (loses money at 59% wins) |
| G2 Overnight gap fill, stop 1.5x the target | MNQ / MES / MGC | 0.67 **violates** | 59.1% 1.19 / 52.8% 0.89 / 49.1% 0.75 | 54.1% 0.82 / 55.2% 0.98 / 49.0% 0.84 | MNQ passes IS, FAILS held-out (-$7,777) |
| M2 Gold overnight-VWAP reversion, stop 1.5x the target | MGC | 0.67 **violates** | 37.5% / 0.43 | 40.9% / 0.46 | fails IS |

Same size, different NOISE versions, held-out (eval pass / eval bust, funded bust, income per 2 weeks) - this is the "does it beat NOISE alone" test:

| version | Pro 50K, 1 micro | Pro 150K, 3 micros (2 under $2,250) |
|---|---|---|
| N0 NOISE alone | 66 / 34, 34%, $27 | 58 / 42, 46%, $52 |
| **N1 NOISE + profit lock** | **77 / 23, 23%, $46** | **70 / 30, 31%, $92** |
| N6 30-minute checks | 60 / 40, 46%, $28 | 50 / 50, 56%, $51 |
| N7 30-minute checks + lock | 67 / 33, 33%, $38 | 59 / 41, 42%, $75 |
| N2 half off at 1R (violates R:R) | 69 / 31, 28%, $32 | 59 / 40, 40%, $88 |
| N3 half off at 0.5R (violates R:R) | 66 / 34, 24%, $16 | 55 / 44, 38%, $59 |

N1 was the best in the pick period (edge ratio 1.63 vs 1.49 for plain NOISE, most profit) and is the best held-out. NOISE is not replaced - it is kept
and improved.

## Sizing and brake per plan, and what safety costs
All rows: NOISE + profit lock. Main number = held-out bootstrap; [pick period in brackets]. "OK" = eval pass >= 60%, eval bust < 35% and funded
year-1 bust < 35% in BOTH periods, and under 35% on the held-out rolling history too. "Cushion" = balance minus the trailing loss limit.

**Pro 25K** (loss limit $1,000, target $1,250)
| size | eval pass / bust | median sessions to pass | funded bust yr 1 | income / 2 wk | OK? |
|---|---|---|---|---|---|
| 1 micro | 56% / 44% [76 / 24] | 38 [52] | 62% [34] | $29 [$76] | no |

Smaller emergency stops ($150, $200) and a daily profit stop were also run on 25K (previous agent's grid, 120-session history): held-out eval bust
stays 47-63% and funded bust 66-81%. Nothing makes 25K safe.

**Pro 50K** (loss limit $2,000, target $3,000)
| size | eval pass / bust | median sessions to pass | funded bust yr 1 | income / 2 wk | OK? |
|---|---|---|---|---|---|
| **1 micro (recommended)** | 77% / 23% [96 / 4] | 143 [166] | 23% [3] | $46 [$72] | yes |
| 2 micros | 54% / 46% [74 / 26] | 48 [63] | 60% [32] | $54 [$139] | no |
| 2 micros, 1 while the cushion is under $600 | 56% / 44% [75 / 25] | 52 [65] | 58% [30] | $56 [$140] | no |
| 2 micros, 1 while the cushion is under $1,000 (today's rule) | 60% / 40% [80 / 20] | 59 [73] | 53% [20] | $59 [$137] | no |
| 2 micros, 1 while the cushion is under $1,400 | 67% / 33% [88 / 12] | 73 [97] | 43% [12] | $58 [$127] | no |

**Pro 100K** (loss limit $3,000, target $6,000)
| size | eval pass / bust | median sessions to pass | funded bust yr 1 | income / 2 wk | OK? |
|---|---|---|---|---|---|
| 1 micro | 83% / 11% [97 / 0] | 352 [352] | 5% [0] | $33 [$46] | yes (very slow) |
| 2 micros | 65% / 35% [88 / 12] | 129 [158] | 38% [11] | $72 [$152] | no |
| 2 micros, 1 while the cushion is under $900 (today's rule) | 68% / 32% [92 / 8] | 137 [163] | 34% [7] | $72 [$151] | yes (thin) |
| 2 micros, 1 while the cushion is under $1,500 | 73% / 27% [95 / 4] | 154 [174] | 24% [3] | $68 [$144] | yes |
| **2 micros, 1 while the cushion is under $2,100 (recommended)** | 78% / 19% [97 / 2] | 197 [207] | 14% [1] | $61 [$126] | yes |
| 3 micros | 51% / 49% [73 / 27] | 68 [88] | 58% [30] | $69 [$178] | no |
| 3 micros, 2 while the cushion is under $1,500 | 54% / 46% [77 / 23] | 73 [95] | 55% [24] | $72 [$179] | no |
| 3 micros, 1 while the cushion is under $1,500 | 62% / 38% [88 / 12] | 96 [123] | 39% [10] | $70 [$164] | no |
| 3 micros, 1 while the cushion is under $2,100 | 70% / 29% [93 / 5] | 142 [176] | 21% [3] | $64 [$138] | yes |

**Pro 150K** (loss limit $4,500, target $9,000)
| size | eval pass / bust | median sessions to pass | funded bust yr 1 | income / 2 wk | OK? |
|---|---|---|---|---|---|
| 2 micros | 80% / 19% [98 / 2] | 250 [259] | 15% [2] | $75 [$128] | yes |
| 2 micros, 1 while the cushion is under $2,250 | 85% / 10% [98 / 0] | 278 [262] | 4% [0] | $69 [$125] | yes (safest) |
| 3 micros | 65% / 35% [88 / 12] | 129 [158] | 37% [10] | $91 [$193] | no |
| 3 micros, 2 while the cushion is under $1,350 | 68% / 32% [90 / 10] | 135 [161] | 34% [8] | $94 [$194] | yes (thin) |
| 3 micros, 2 while the cushion is under $2,250 (today's funded rule) | 70% / 30% [93 / 7] | 144 [168] | 31% [6] | $92 [$190] | yes (thin) |
| 3 micros, 2 while the cushion is under $3,150 | 73% / 27% [95 / 5] | 161 [183] | 25% [4] | $89 [$176] | yes |
| **3 micros, 1 while the cushion is under $2,250 (recommended)** | 77% / 18% [96 / 1] | 182 [184] | 11% [1] | $79 [$174] | yes |
| 3 micros, 1 while the cushion is under $3,150 | 79% / 9% [95 / 0] | 256 [231] | 3% [0] | $63 [$134] | yes |
| 4 micros | 55% / 45% [78 / 22] | 82 [105] | 53% [21] | $87 [$221] | no |
| 4 micros, 2 while the cushion is under $2,250 (today's eval rule) | 63% / 37% [85 / 15] | 105 [122] | 42% [12] | $94 [$213] | no |
| 4 micros, 2 while the cushion is under $3,150 | 68% / 32% [90 / 9] | 123 [147] | 33% [6] | $91 [$194] | yes (thin) |
| 4 micros, 1 while the cushion is under $2,250 | 69% / 27% [94 / 3] | 142 [151] | 17% [2] | $78 [$187] | yes |

**The income cost of staying under 35% bust**
- In the hard (held-out) years there is almost **no** cost: bigger size does not pay more because the extra accounts die. On 150K every size from 3
  to 4 micros pays $78-$94 per 2 weeks; the recommended one pays $79 with an 11% funded bust instead of 31-53%.
- In the easy (pick) years the cost is real: 150K recommended $174 per 2 weeks vs $221 at 4 micros flat (-21%); 100K $126 vs $178 at 3 micros
  (-29%); 50K $72 vs $139 at 2 micros (-48%).
- The recommended rows keep bust at 25% or less, a 10-point safety margin under your 35% limit. If you want the most income that still stays under
  35%: 100K "2 micros, 1 under $1,500" ($68 / 24% bust) and 150K "3 micros, 2 under $2,250" ($92 / 31% bust, eval pass 70% in ~144 sessions). The
  margin there is thin (30-31% against a 35% limit, with about +-3 points of sampling error).

## Honest limits of this study
1. **The sizing was NOT a clean held-out pick.** Sizing picked on 2021-23 alone fails in 2024-26: for example 150K "4 micros" looks fine in the pick
   period (eval bust 22%, funded bust 21%, $221) and then busts 45% of evaluations and 53% of funded accounts held-out. Reason: the Nasdaq was about
   68% higher in 2024-26 (average 23,006 vs 13,722), so each micro swings more in dollars (per-trade swing $181 -> $289) while Lucid's loss limits stay
   the same dollars. So the sizes above were chosen to hold in BOTH periods, with a 10-point margin. The strategy choice (profit lock) was a clean
   pick-then-judge, with one caveat: session 11 had already looked at its held-out result when proposing D75-P1.
2. **If the index keeps rising, one micro keeps getting bigger.** Re-check the sizes when MNQ is ~25% above today's level; the remedy is fewer micros
   or a bigger plan.
3. Bootstrap paths shuffle 10-session blocks, so very long losing regimes are under-represented; the rolling history has only 2-3 independent
   windows. Read every percentage as +-5 points.
4. Not modelled: evaluation and reset fees (so "income" is before fees), news blackouts, slippage above 1 tick, any Lucid time limit or inactivity
   rule on evaluations (a 7-9 month evaluation must be allowed - **verify with Lucid**), the D57 stop-shrink / freeze logic of the live app.
5. Year-1 funded income is small partly because Lucid pays only above the buffer (balance must first climb the full loss-limit amount + $100).
6. Results are for the rules as traded in research (`lib.noise_stream`); the live app does not have the profit lock yet.

## What this means for the app (proposals only - nothing was built or changed)
1. Add the NOISE profit lock (+100 points -> stop at entry + 10 points; locked stop-out ends NOISE for the day) = D75-P1.
2. Switch the afternoon fade off (no causal edge, session 14 D81).
3. Size table: 50K 1 micro; 100K 2 micros with the brake at 70% of the loss limit (1 micro under $2,100); 150K 3 micros with the brake to 1 micro
   under $2,250 - the same in evaluation and funded stages. Retire the 25K and the High-risk / Evaluation-Mode boosts for this strategy.
4. Rebuild the dashboard projection (`main_strategy_5y.csv`) on the N1 stream once 1-3 are approved.

## Files
`lib.py` (causal trade generators, cost model, account engine) - `candidates.py`, `candidates2.py`, `candidates3.py` (the 21 ideas) - `account.py`
(bootstrap + rolling tests, one-position merge) - `matrix.py` (NOISE versions x plans x sizes) - `final.py` (today's baseline, brake list, lock
sensitivity) - `report.py` (prints these tables, writes `out/recommend.json`) - `make_pdf.py` -> `Paytience_best_strategy_lucid.pdf` -
`build_raw.py` (joins the Databento downloads) - `run_step12.py`, `pick.py`, `out/grid_*.json`, `out/picks_*.json` (previous agent's 3,564-setting
grid; kept for the record, NOT used for the recommendation because it counted frozen accounts as alive) - `out/*.json`, `out/streams/*.csv` (every
trade of every candidate).
Re-run: `export S15_RAW=<folder with mnq_5y.csv mes_5y.csv mgc_5y.csv>`; `python3 candidates.py; S15_TAG=mnq S15_SYMS=MNQ python3 candidates2.py`
(also `mes`, `mgc`); `python3 candidates3.py; python3 matrix.py; python3 final.py; python3 report.py; python3 make_pdf.py`.
