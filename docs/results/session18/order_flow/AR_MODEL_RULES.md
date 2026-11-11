# "Complete Orderflow Trading Course (AR Model)" — Christopher Creamer (thraxxtrades), MAIN TEACHER
Source: full transcript pasted by the user 2026-11-11 (distilled here by us, not verbatim). Chapter timestamps in brackets.
Trades NQ/MNQ and gold; AM session only (first ~1.5 h of NY open); tools: ATAS/DeepCharts footprint, TradingView, Tanuki (GEX).

## Framework (order matters — "the signal comes last, not first")  [0:00-16:45, 57:35-1:13:54]
1. ENVIRONMENT/CONTEXT: classify the day. Balance<->imbalance cycle; structure (HH/HL/LH/LL) on 4h/1h/15m/5m; gamma environment.
   Three environments: INITIATIVE EXPANSION (directional, acceptance outside range, follow-through) -> continuation models;
   BALANCE ROTATION (two-sided, repeated rejection at extremes) -> reversal at extremes, continuation models degrade;
   LOW PARTICIPATION / COMPRESSION (tight overlapping candles, failed micro-breakouts, slow tape) -> most models fail: DON'T TRADE.
   Reversal models in expansion only at extreme HTF location with acceptance failure. Scalping suffers most in compression (avg win shrinks vs fixed stop).
2. LOCATION: buy discount in bullish bias, sell premium in bearish. Fixed-range volume profile from the swing low to swing high (VAH/VAL/POC),
   range Fibonacci with levels 0.5, 0.62, 0.705, 0.788, 0.886, 1.1. Focus zone = 0.705-0.886 (discount below value for longs, premium above for shorts).
   A CLOSE beyond 0.886 invalidates the reversal idea (shift to continuation); 1.1 touch = continuation. Draw one side only (the bias side).
   Premium/discount is a location filter, not a signal; must agree with higher-timeframe bias (top-down: daily/4h/1h before 5m/15m).
   Also: gamma levels (call wall, put wall, gamma flip/HVL), resting liquidity at round numbers/highs/lows.
3. PATH: how the daily candle forms across Asia -> London -> New York. Asia = balance/anchor; London often makes the wick/manipulation;
   NY resolves direction or continues. His NQ volatility indicator: Asia high/low (locked at session close) + daily ATR(20) -> asymmetric
   statistical zones above/below Asia: Level 1, AVR-, AVR (avg expansion), AVR+ (extended), MAX (outlier). Quarters/EQ of Asia range. Use only as
   LOCATION/exhaustion reference WITH a daily bias; never trade just because price touches a zone; on normal days price returns to Asia range.
4. CONFIRMATION (footprint): effort vs result. Only after 1-3 align.

## Order-flow definitions  [24:00-35:00, 37:00-57:00, 2:46:53-3:15:00]
- Aggressive = market orders (crossing spread); passive = limit orders. Price moves only when aggressive flow overwhelms resting liquidity.
- Footprint: bid x ask per price; delta = ask volume - bid volume; imbalance = >= 4x (400%) diagonally (bid at price vs ask one price up);
  stacked imbalances (consecutive) = one-sided pressure and later support/resistance; POC inside candle shows where business was done.
- Aggression alone != direction; ACCEPTANCE moves price. Heavy volume at highs with no continuation = absorption; absorption != reversal
  (can be pause before continuation / inventory transfer). Need: location + failed initiative + pressure flip (delta flip) + price response shift.
- Delta flip only matters at a structural inflection after failed initiative with a measurable response; delta flips inside chop = noise.
- Absorption = high effort / low result at meaningful location; exhaustion = participation dries up (low effort/low result). Absorption in the
  middle of balance = noise.
- Volume profile roles: session (RTH) profile for context (VAH/VAL/POC/HVN/LVN, value acceptance vs rejection), fixed-range profile over an
  expansion leg to narrow location, per-candle mini-profile for execution refinement. LVN = location candidate, not an auto-entry; POC not a magnet in trends.

## Entry model (absorption)  [3:20-3:23 and live examples]
- Confirmation candle (shows absorption/reversal evidence at location) then ENTRY candle that opens and immediately pulls back into the confirmation
  candle, preferably into its low-volume nodes / stacked imbalances / prior candle POC. Stop = beyond where the absorption happened (other side of the
  absorbed aggressors). Targets: structure/HTF draw, put/call wall, P1/P2 levels, Asia range return.
- Positive gamma = mean-reversion/compression expectation: fade failed breakouts, take profits quicker, tighten trailing; negative gamma = expansion
  expectation: hold/let run. Order flow overrides gamma when they disagree (trade the tape).
## Management (live sessions)  [3:30-3:50]
- Trail stop behind each new structure: above the POC of the last 5-min/15-min candle, above large resting sellers / below large buyers; breakeven once
  follow-through appears; tighten when the move hits a prior absorption zone or compresses. ~50-pt NQ targets per trade (two wins of ~50 pts, 71/85/104-pt days).
- Large 5m ATR (e.g. 81 pts) = trade much smaller or stand aside; stop for the day when compressing/choppy or green on the day ("don't mess it up").
## Risk / survivability  [3:50-4:25]
- Hard daily loss limit and trade limit; close the platform at the limit; no size increase after losses (tilt = behaviour, not feeling); reduce size after
  emotional escalation; earn the right to scale; not trading is a position; ignore signals when environment/location/participation don't align.
## What we can/cannot test with cached 1-minute bars (no tick data)
Testable approximations: environment classification (ATR/range/overlap), premium/discount via swing range + fib 0.705-0.886 + volume-profile VAH/VAL,
Asia-range + ATR(20) volatility zones (needs only OHLC), session timing, top-down structure bias, estimated absorption/delta flips from close-location
volume, confirmation+entry candle pattern, stop/trail rules. NOT testable: true aggressor delta, stacked imbalances, heat-map/DOM liquidity, gamma levels.
