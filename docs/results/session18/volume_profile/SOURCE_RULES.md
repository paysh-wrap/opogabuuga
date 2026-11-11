# Source: tradealgo.com "Strategy 5: Volume Profile Trading" (user screenshots 2026-11-11) — claims are UNVERIFIED
- Key levels: POC (highest-volume price), VAH/VAL (range holding 70% of volume), HVN (magnets), LVN (thin air, price moves fast through).
- "80% rule" (Market Profile): price opens inside prior session's value area, moves to one extreme -> ~80% chance it traverses to the opposite extreme. (claim)
- System, previous-day volume profile on ES (scale points for MNQ/MGC):
  1. Plot previous session's profile; identify POC, VAH, VAL.
  2. Open ABOVE VAH: bullish -> buy dips to VAH, stop 8 points below.
  3. Open BELOW VAL: bearish -> sell rallies to VAL, stop 8 points above.
  4. Open INSIDE value area: range day -> fade extremes (buy near VAL, sell near VAH).
- Claimed win rate 55-65% with the value-area filter. (claim — test it)
