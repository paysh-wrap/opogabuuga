# Rules distilled from "How To Trade Order Flow In 2026 (4 Hours)" — Jesse Rogers | Casper Trading
Source: transcript pasted by the user (2026-11-11). This is a condensed rules summary written by us, not the transcript.
Teacher's framework = **CZT: Condition → Zone → Trigger.** All three must be clear, else no trade.

## Two foundations
1. **Auction market theory**: balance → shift → imbalance → new balance. Acceptance = price stays outside old value with
   time + volume + price (-> trend/breakout). Rejection = quick, low-volume, fast return (-> failed auction, reversal).
2. **Return on effort**: aggression (market orders: delta/CVD/bubbles) is "effort"; price is the result.
   - Aggression = effort rewarded (candle closes in aggressors' direction) -> that side in control.
   - Absorption = big effort, no result (close away from aggressors' direction; passive limit orders absorb) -> reversal.
   - Exhaustion = aggression dies off at a key zone (CVD flattens, volume drops, wicks) -> control shifts soon.

## Condition (bias / day type)
- Where is value? Prior RTH (09:30-16:00) volume profile: VAH / VAL (70% of volume), POC; weekly profile too.
- Open vs prior value area: above = bullish lean (value up), below = bearish lean, inside = chop until it breaks.
- Premium = above value, discount = below. Buyers buy cheap, sellers sell expensive.
- Profile shapes: D = balanced (chop, reversals), P = accepted higher (bullish), B = accepted lower (bearish),
  thin = strong trend. LVN = fast-move pocket (real fair-value gap); HVN = acceptance.
- Gamma environment (needs options data — NOT available to us): positive GEX = dampened, mean-reverting -> buy dips/sell rips,
  reversal playbook (absorption/exhaustion at round numbers); negative GEX = amplified, breakouts -> trade aggression, trail hard.
  Teacher's stats (ES 2024-26): value-above-yesterday + negative gamma -> 74% chance morning extreme is exceeded; first-candle
  breakouts ~1.7x larger follow-through in negative gamma.
- Context beats signals. Day-before-news / flat-looking days (levels very close together) = low risk or no trade.
- "Band extreme": if price is at the model's day high/low (74% bound), don't take trades in that direction.

## Zone
Prior-day VAH/VAL/POC, weekly levels, LVNs, round numbers (option strikes), swing highs/lows, gamma levels, pre-market
extremes where aggressors got absorbed.

## Trigger (order flow)
- Reversal playbook: at a zone, aggressors push but get no return (absorption) or fade out (exhaustion), then the other
  side gets a return on effort -> enter. Stop just beyond the zone/where the absorbed aggressors sit (not on the round number: +2-3 ticks).
- Continuation playbook: breakout of balance with aggression that gets a return and acceptance (volume + time) -> enter;
  or wait for a retrace to the aggressor zone and absorption there.
- Both: price confirms (candle closing away from the trapped side).

## Management
- No fixed take-profit. Trail the stop behind each new balance / below the last zone where the opposing side was wrong.
- Strength of trend: shallow retrace into aggressor zone = strong; deep retrace = weaker. Get aggressive near big round numbers/key levels.
- Exit when control shifts: exhaustion (CVD flat, volume dying), opposing aggression getting a return, accepted back through the balance.
- Low-conviction/choppy days: ~half risk, one attempt; be wider in positive gamma; if a first idea fails, re-read the market (condition may have flipped).
- Entries early in RTH (first minutes after 09:30) want fast follow-through; if not, expect chop.

---
## Addendum (full transcript re-pasted 2026-11-11): order-flow-only timestamp index + worked examples
Only order-flow/strategy content is used; intro/sales/psychology/comments/recommendations are ignored.

| Time | Topic (order flow only) |
|---|---|
| 2:10-13:30 | Auction market theory: balance/shift/imbalance, acceptance vs rejection, premium/discount |
| 14:00-20:40 | Order book: passive (limit) vs aggressive (market); absorption defined |
| 20:47-25:00 | Return on effort: aggression / absorption / exhaustion defined |
| 31:00-36:30 | Delta, CVD, footprint, heat map, big trades |
| 36:46-45:00 | Aggression patterns (price confirms effort; trail stops under aggressor zones) |
| 45:00-56:48 | Absorption patterns (big effort, close away from it; CVD falls but price flat) |
| 56:48-1:05:00 | Exhaustion (aggression into zone dies: volume drops, CVD flattens, wicks) |
| 1:05:00-1:41:48 | Volume profile: RTH 09:30-16:00, VAH/VAL/POC (70%), HVN/LVN, D/P/B/thin profiles, value up/down, open vs prior value |
| 1:42-2:19 | Gamma (needs options data - not available; stats listed in the first section) |
| 2:19:18-2:35 | CZT process: condition -> zone -> trigger; no-trade rules; band extreme |
| 2:35-2:40 | Trade management: trail behind each new balance; who is in control |
| 2:40-4:20 | Live examples (below) |

### Worked examples (all use the same logic)
1. **Positive-gamma fade**: value trending down, open conflicting; pre-market tapped an LVN; at a round number (29,400) buyers
   aggressive with no return, passive sellers absorbing, CVD tops -> short after sellers get a return; stop just above the round number;
   low risk (~half), at most one more attempt after a loss; first idea failed (stopped), second (same logic) won after trailing.
2. **Negative-gamma value-down trend day**: open below prior value AND weekly value, inside an LVN; huge aggressive selling with
   rising volume (opposite of exhaustion); short on the opening drive; stop moved up after every balance/pivot, to entry once
   price stalled, tighter near round numbers (29,000); exit on rebound/loss of control. ~$10k in ~15 min.
3. **Gap-and-go long**: open above prior VAH (bullish condition); first minutes sellers hit into passive buyers at VAH and are absorbed
   (zone = prior VAH, trigger = absorption + buyers get a return); stop under the absorbed low; trail up under each new balance and under
   aggressor zones; aggressive trail at round number 28,000.
4. **Plan fails**: bullish lean (open above value) but price blasts through every level with heavy aggression and no passive buyers ->
   drop bias, short the retrace into the broken balance after sellers keep getting a return; stop above where recent aggressors sat
   (+ticks), to entry quickly, trail above round number; out when volume/CVD momentum dies. "If you're wrong there is often a better trade."

### Implementable rules for our bar-only tests (what was already tested in of1y/czt1y)
open vs prior-RTH value area (VAH/VAL/POC from 1m volume), premium/discount, zone = prior VAH/VAL/POC + round numbers (100/50 pts) +
LVN, trigger = estimated absorption/exhaustion/aggression-with-acceptance, stop beyond zone (+2-3 ticks), trail behind balances, no
trade when levels bunched / at the day band extreme. Result so far: no edge on the estimated-bar proxy (see RESULTS.md); real footprint
data needed.

---
## Deep-read addendum #2 (details not captured above; from the full transcript)
Entry timing / confirmation
- Don't enter on the first spike: let "the smoke clear" — want follow-through and some volume/time (acceptance) first, then enter; pre-stage the order at the stop level.
- Pre-market reaction at a zone must be confirmed by follow-through in RTH (real volume) fast: within ~4 minutes of 09:30; if the move doesn't come quickly, grade the day as likely chop.
- Entries after absorption can be taken late: use the absorption/aggressor zone as the new support/resistance and wait for a retrace into it.
- Price confirms order flow: the candle must close away from the trapped side; effort with no close-through = no return.
Reversal vs continuation
- Reversal playbook needs a zone + opposing aggression that FAILS (absorbed) + the other side getting a return; continuation needs aggression that gets a return AND acceptance (time/volume) outside balance.
- A reversal at a level that is "accepted" (price hangs there, volume builds) = likely a fake-out against the reversal — do not fade it.
- P/B profiles flip at key zones: a P-day (bullish) into a big resistance level can still reverse; trust the live order flow over the prior-day lean.
- Low-volume nodes: price moves through them fast; when accepted inside one with aggression, expect a fast one-sided move (his favourite days). Teacher equates LVNs with "real fair value gaps".
- Failed auction / rejection of VAL = bullish (buyers defended discount); rejection of VAH = bearish.
- Prior-day close/open: open above prior close/value = accepted higher.
Risk and stops
- Stop just beyond the absorbed aggressors / last pivot / balance base; never exactly on a round number (+1-3 ticks); wider in positive gamma/chop.
- Example sizing: NQ 3 contracts, ~15-50 pt stops, $2-5k risk; on low-probability days risk about half (feeler trade), max one extra attempt after a loss; never exceed the daily risk limit.
- De-risk: move stop to entry once price has paid and stalls; trail under each new pivot/balance; trail faster near big round numbers/prior highs; re-enter if stopped at entry and the setup re-forms.
- No take-profit orders: exit when control shifts (aggressors defended less, CVD flat while volume dies, price re-accepted back through the balance). "See green, take green" only with logic.
Reading the book / tape
- Passive orders pulled as price approaches (bids disappearing) = buyers not confident; walls being eaten = aggressors in control; asks moving lower = very bearish; thin book on one side = path of least resistance.
- Spoofing/pulled liquidity is read from the heat map; stops are invisible until triggered (turn into market orders).
Day filters
- Skip/low risk: levels bunched close together, flat/boring days, day before major news (CPI/FOMC) unless clear; at the "band extreme" of the day's modelled range only trade reversals.
Not testable with our data: heat-map/DOM behaviour, true aggressor delta, gamma levels/environment, weekly profile LVNs without enough history.
