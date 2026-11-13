"""D55: research results shown next to each strategy button (static facts — NOT live data).

B7 / D135 (session 20): the NOISE and MAIN cards are re-based on the session-19 study of the SHIPPED config
(docs/results/session19/refine/RESULTS.md R6 + docs/results/session19/shipped_config.md): Databento MNQ 1-minute
2019-05 → 2026-11 (7.5 yr), NOISE preset C ($250 stop, +100 pt → entry +10 profit lock) with Mondays off, the fade on
days NOISE did not trade (Mondays off), 1 micro, costs included. Eval pass / bust (D137) are NOT stored here: they are
read from config/eval_odds.yaml for the active plan, size table and EOD-toggle state. News and intraday MLL touches
are not modeled. The other cards keep their own (older or not back-testable) notes.
"""

from __future__ import annotations

CATALOG: list[dict[str, object]] = [
    {
        "key": "pm_fade",
        "name": "MAIN — NOISE + Afternoon fade ($250 stops, MNQ)",
        "source": "D58 / D132: NOISE (profit lock, $250 stop, Mondays off) + 13:00–15:29 VWAP ±2 sd fade on days NOISE "
        "didn't trade (Mondays off)",
        "verified": True,
        "status": "MAIN",
        "win_pct": 52.9,
        "profit_factor": 1.38,
        "usd_per_trade": 18.54,
        "trades_per_week": 3.9,
        "held_out_trades": 192,
        "pro25k_pass_pct": None,  # D137: injected from config/eval_odds.yaml by api/dashboard.py (active plan / table)
        "pro25k_bust_pct": None,
        "period": "7.5 years 2019-05 → 2026-11 (1,535 trades, +$28,452 at 1 micro); held-out last 12 months: win "
        "59.9%, PF 1.69",
        "note": "Turns NOISE + the fade on together. On EVAL accounts the fade is OFF by default (toggle below): NOISE "
        "alone passes more evaluations (pass / bust shown above and in the toggle below); funded accounts keep the "
        "fade for the extra profit.",
        "also": ["strategy.noise"],
    },
    {
        "key": "noise",
        "name": "NOISE — intraday momentum (MNQ)",
        "source": "Zarattini, Aziz & Barbon 2024, 'Beat the Market' (noise-area bands, VWAP trail)",
        "verified": True,
        "status": "VERIFIED",
        "win_pct": 50.1,
        "profit_factor": 1.49,
        "usd_per_trade": 24.86,
        "trades_per_week": 2.4,
        "held_out_trades": 121,
        "pro25k_pass_pct": None,  # D137: injected from config/eval_odds.yaml by api/dashboard.py
        "pro25k_bust_pct": None,
        "period": "7.5 years 2019-05 → 2026-11 (935 trades, +$23,242 at 1 micro); held-out last 12 months: win 59.5%, "
        "PF 1.72",
        "note": "Hourly checks 10:00–15:00, exit on band/VWAP, $250 emergency stop per micro, profit lock (+100 pt → "
        "stop to entry +10, then done for the day), Mondays off, flat 16:00. Warm-up: 10 sessions of TradingView "
        "1-minute bars.",
    },
    {
        "key": "ai_bias",
        "name": "AI only — TradingAgents + Vibe-Trading (MNQ)",
        "source": "D56: both tools must agree strongly on the day's side; enter 09:31, 0.5% stop, flat 16:00",
        "verified": False,
        "status": "UNVERIFIED",
        "win_pct": None,
        "profit_factor": None,
        "usd_per_trade": None,
        "trades_per_week": 1.35,
        "held_out_trades": 0,
        "pro25k_pass_pct": None,
        "pro25k_bust_pct": None,
        "period": "NOT back-testable (LLMs can't be run on past dates). Hindsight 1y MNQ, 1 micro, per trade: "
        "perfect call +$267 (PF 5.3) · 70% +$111 · 60% +$59 · 55% +$33 · 50% +$8. Real LLM accuracy ≈ 50–55%.",
        "note": "Only trades on days both tools agree (~27% of days). Real results build in the AI ledger; "
        "the AI bias stays advisory until the ledger proves ≥ 70% accuracy.",
    },
    {
        "key": "ai_duo",
        "name": "AI Duo — both AIs agree, VWAP pullback entry (MNQ + MGC)",
        "source": "D83: TradingAgents + Vibe-Trading must pick the same side (Vibe only gives an opinion); first "
        "5-min VWAP pullback close 03:00–11:30 ET (09:30–09:35 excluded); structure stop capped at the NOISE $ "
        "stop; 2.0R target (floor 1.5R); 1 micro; MNQ and MGC",
        "verified": False,
        "status": "UNVERIFIED",
        "win_pct": None,
        "profit_factor": None,
        "usd_per_trade": None,
        "trades_per_week": 1.35,
        "held_out_trades": 0,
        "pro25k_pass_pct": None,
        "pro25k_bust_pct": None,
        "period": "NOT back-testable (LLM calls can't be run on past dates). Needs ~27% of days where both agree; "
        "break-even win rate at 2R is about 38%.",
        "note": "Window 03:00 (London open) → 11:30 ET and markets MNQ / MGC are editable in My Settings (MGC: AI "
        "Duo only, NOISE stays MNQ). Never trades when the AIs disagree, either fails or says NEUTRAL; never "
        "opposite a NOISE position (hedge lock: NOISE open → Duo skips, Duo open first → NOISE blocked, same-bar "
        "tie → NOISE wins). Every day logs a decision with a reason code. Unverified (not back-testable).",
    },
    {
        "key": "noise_ai_split",
        "name": "NOISE + AI Duo — 50/50 risk split",
        "source": "D92: with NOISE and AI Duo both on, each side trades half size (rounded down, minimum 1 micro) "
        "and may use half of the daily loss limit",
        "verified": False,
        "status": "UNVERIFIED",
        "win_pct": None,
        "profit_factor": None,
        "usd_per_trade": None,
        "trades_per_week": None,
        "held_out_trades": 0,
        "pro25k_pass_pct": None,
        "pro25k_bust_pct": None,
        "period": "NOT measured: the AI Duo half cannot be back-tested. NOISE alone stays the main strategy.",
        "note": "Default OFF. Turns NOISE and AI Duo on together. Only tightens: every other size, DLL, MLL, "
        "consistency and hedge-lock check still applies.",
        "also": ["strategy.noise", "strategy.ai_duo"],
    },
    {
        "key": "order_flow",
        "name": "Order Flow — TradingView order-flow alerts (MNQ + MGC) — UNVERIFIED",
        "source": "D101 AR Model (main teacher, D100): ENVIRONMENT (expansion / rotation; compression = no trade) → "
        "LOCATION (swing fib 0.705–0.886 + fixed-range value area) → PATH (Asia range + daily ATR(20) zones) → "
        "CONFIRMATION (absorption / delta flip / stacked imbalance candle, then a pullback entry candle) from the Pine "
        "indicator 'Paytience Order Flow' (real TradingView footprint delta when available, else estimated — sent as "
        "delta_source) → webhook alert; stop beyond the absorption zone, 2R target, 1 micro",
        "verified": False,
        "status": "UNVERIFIED",
        "win_pct": None,
        "profit_factor": None,
        "usd_per_trade": None,
        "trades_per_week": None,
        "held_out_trades": 0,
        "pro25k_pass_pct": None,
        "pro25k_bust_pct": None,
        "period": "NOT tested on real order flow. Session-18 AR study on ESTIMATED 1-minute delta: the full 4-layer "
        "model did not beat NOISE; location and path did not help (they are switches in the plan file).",
        "note": "Default OFF. Needs the 'Paytience Order Flow' alert on a 1-minute MNQ1! and/or MGC1! chart (D96: MGC "
        "is on for Order Flow only — every other strategy keeps gold off). The app rebuilds stop and target itself "
        "(never trusts the alert's prices); window, news, hedge lock (METALS for MGC), DLL, consistency and the "
        "16:00 ET flat all still apply. 1 micro.",
    },
    {
        "key": "order_flow_amt",
        "name": "AMT+ Order Flow — context → location → order flow last — UNVERIFIED",
        "source": "D110 prop-firm trader (trades Lucid; docs/results/session18/order_flow/AMT_PLUS_RULES.md): CONTEXT "
        "(acceptance above / below the prior RTH value area at the session open; balance = stand aside or VA edges) → "
        "LOCATION (ETH VWAP, prior VAH / VAL / POC, LVN / single prints, delta outlier, prior-session high / low) → "
        "the Order Flow signal LAST; target = the next key level when it gives 1.5–3R, else 2R",
        "verified": False,
        "status": "UNVERIFIED",
        "win_pct": None,
        "profit_factor": None,
        "usd_per_trade": None,
        "trades_per_week": None,
        "held_out_trades": 0,
        "pro25k_pass_pct": None,
        "pro25k_bust_pct": None,
        "period": "NOT tested (no real order-flow data). The trader's own claims (43% win, avg win/loss 3.5) are not "
        "verified by us.",
        "note": "Default OFF. Adds the AMT+ gates to the Order Flow strategy (turns Order Flow on with it); "
        "only removes trades (codes OF_AMT_*). Needs the current 'Paytience Order Flow' indicator "
        "(sends context + key level). "
        "Every Order Flow and Lucid gate still applies. 1 micro.",
        "setting_key": "strategy.order_flow_cfg.amt.enabled",
        "also": ["strategy.order_flow"],
    },
    {
        "key": "order_flow_zone",
        "name": "Order Flow · ATR zones (iceberg PROXY) — UNVERIFIED",
        "source": "D111 Scott / Chart Fanatics (docs/results/session18/order_flow/ICEBERG_ATR_RULES.md): volume EVENT "
        "(iceberg PROXY = footprint absorption / large volume, no MBO data) + ATR(5m) zones. POSITION: entry 115% ATR "
        "outside the zone, stop back through the zone + 115% ATR, trail only to new events (never breakeven). "
        "REVERSION: 1/2/3 ATR away back to the zone, stop at the next ATR; exit on an opposing event",
        "verified": False,
        "status": "UNVERIFIED",
        "win_pct": None,
        "profit_factor": None,
        "usd_per_trade": None,
        "trades_per_week": None,
        "held_out_trades": 0,
        "pro25k_pass_pct": None,
        "pro25k_bust_pct": None,
        "period": "NOT tested (no MBO / real order-flow data); the trader's claims are not verified by us.",
        "note": "Default OFF. A separate Order Flow type (turns Order Flow on with it). Filters: dead zone 11:15–13:30 "
        "ET needs relative volume ≥ 150%, no new trades in the last 10 min of RTH, price-change confirm, TICK "
        "program-day no-fade, min event size 150. Codes OF_ZONE_*. 1 micro; every Lucid gate applies.",
        "setting_key": "strategy.order_flow_cfg.zone_atr.enabled",
        "also": ["strategy.order_flow"],
    },
]
