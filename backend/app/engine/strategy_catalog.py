"""D55: research results shown next to each strategy button (static facts from the session 9 study — NOT live data).

Source: docs/results/2026-11-09_session9_strategy_research.md (Databento MNQ 1-minute 2019-05 → 2026-11, pick on
2019–2023, judge unchanged on 2024-01 → 2026-11, 1 micro, costs included). Pro 25K figures: tools/sim25k.py rolling
starts on real held-out days (eval: +$1,250 target, $1,000 EOD trailing max loss; open-trade drawdown and news not
modeled → somewhat optimistic). The LunqFX row is the engine's own 1-year run (D52/D54)."""

from __future__ import annotations

CATALOG: list[dict[str, object]] = [
    {
        "key": "pm_fade",
        "name": "MAIN — NOISE + Afternoon fade ($250 stops, MNQ)",
        "source": "D58: NOISE (fixed $250 emergency stop) + 13:00–15:29 VWAP ±2 sd fade on days NOISE didn't trade",
        "verified": True,
        "status": "MAIN · fade on PAPER first",
        "win_pct": 50.0,
        "profit_factor": 1.33,
        "usd_per_trade": 19.63,
        "trades_per_week": 5.2,
        "held_out_trades": 1291,
        "pro25k_pass_pct": 65.7,
        "pro25k_bust_pct": 32.2,
        "period": "5 years 2021-11 → 2026-10 (Databento MNQ, 1 micro): +$25,345, no losing full year; pass 71% "
        "(2021–23) / 66% (2024–26)",
        "note": "Turns NOISE + the fade on together. The fade trades paper accounts only until it proves itself live. "
        "Grid of stop sizes: fade $200–400 all ≈ equal; NOISE $250 is a narrow peak (±$50 → ≈ 60% pass).",
        "also": ["strategy.noise"],
    },
    {
        "key": "noise",
        "name": "NOISE — intraday momentum (MNQ)",
        "source": "Zarattini, Aziz & Barbon 2024, 'Beat the Market' (noise-area bands, VWAP trail)",
        "verified": True,
        "status": "VERIFIED",
        "win_pct": 45.0,
        "profit_factor": 1.33,
        "usd_per_trade": 25.81,
        "trades_per_week": 3.0,
        "held_out_trades": 440,
        "pro25k_pass_pct": 56.9,
        "pro25k_bust_pct": 42.2,
        "period": "held-out 2024-01 → 2026-11",
        "note": "Hourly checks 10:00–15:00, exit on band/VWAP, 1% emergency stop, flat 16:00. Warm-up: 10 sessions "
        "of TradingView 1-minute bars.",
    },
    {
        "key": "lunqfx",
        "name": "LunqFX fractal (original strategy)",
        "source": "ICT/LunqFX C1→C2 sweep + CISD (BigBeluga MSO optional, off by default, D91)",
        "verified": False,
        "status": "ORIGINAL",
        "win_pct": 35.0,
        "profit_factor": 1.07,
        "usd_per_trade": 1.98,
        "trades_per_week": 4.7,
        "held_out_trades": 248,
        "pro25k_pass_pct": None,
        "pro25k_bust_pct": None,
        "period": "engine, Nov 2025 → Oct 2026 (MNQ, from 03:00)",
        "note": "No credible independent evidence for sweep/CISD setups; kept as a button. Off = runs in SHADOW. "
        "Without BigBeluga MSO (default, D91) it is untested and always SHADOW.",
    },
    {
        "key": "open_drive",
        "name": "Opening-drive pullback (MNQ) — paper only",
        "source": "Session 9 research (mean-reversion agent): 09:30–10:00 drive → 38.2% pullback limit",
        "verified": False,
        "status": "PAPER ONLY",
        "win_pct": 58.3,
        "profit_factor": 1.29,
        "usd_per_trade": 9.95,
        "trades_per_week": 0.75,
        "held_out_trades": 108,
        "pro25k_pass_pct": 4.8,
        "pro25k_bust_pct": 8.8,
        "period": "held-out 2024-01 → 2026-11 (2019–2023: PF 1.00, not verified)",
        "note": "R:R ≈ 0.95 (below 1.5). At 1 micro most evals neither pass nor bust within 120 days. "
        "Trades paper accounts only until it proves itself.",
    },
    {
        "key": "ai_bias",
        "name": "AI only — TradingAgents + Vibe-Trading (MNQ) — paper only",
        "source": "D56: both tools must agree strongly on the day's side; enter 09:31, 0.5% stop, flat 16:00",
        "verified": False,
        "status": "PAPER ONLY",
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
        "paper accounts only until the ledger proves ≥ 60% accuracy.",
    },
    {
        "key": "ai_duo",
        "name": "AI Duo — both AIs agree, VWAP pullback entry (MNQ + MGC) — paper only",
        "source": "D83: TradingAgents + Vibe-Trading must pick the same side (Vibe only gives an opinion); first "
        "5-min VWAP pullback close 03:00–11:30 ET (09:30–09:35 excluded); structure stop capped at the NOISE $ "
        "stop; 2.0R target (floor 1.5R); 1 micro; MNQ and MGC",
        "verified": False,
        "status": "PAPER ONLY",
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
        "tie → NOISE wins). Every day logs a decision with a reason code. Paper accounts only until the AI "
        "ledger proves ≥ 70%.",
    },
    {
        "key": "noise_ai_split",
        "name": "NOISE + AI Duo — split risk 50/50 — AI Duo paper only",
        "source": "D92: with NOISE and AI Duo both on, each side trades half size (rounded down, minimum 1 micro) "
        "and may use half of the daily loss limit",
        "verified": False,
        "status": "PAPER ONLY",
        "win_pct": None,
        "profit_factor": None,
        "usd_per_trade": None,
        "trades_per_week": None,
        "held_out_trades": 0,
        "pro25k_pass_pct": None,
        "pro25k_bust_pct": None,
        "period": "NOT measured: the AI Duo half cannot be back-tested. NOISE alone stays the main strategy.",
        "note": "Default OFF. Turns NOISE and AI Duo on together. Only tightens: every other size, DLL, MLL, "
        "consistency and hedge-lock check still applies. AI Duo never sends an order to a non-paper account; "
        "there NOISE still trades at half size.",
        "also": ["strategy.noise", "strategy.ai_duo"],
    },
    {
        "key": "order_flow",
        "name": "Order Flow — TradingView order-flow alerts (MNQ) — UNVERIFIED · paper only",
        "source": "D95: Pine indicator 'Paytience Order Flow' (lower-timeframe up/down volume delta, cumulative delta, "
        "session POC / value area): absorption, delta divergence, stacked-imbalance proxy, liquidity sweep, POC magnet "
        "→ webhook alert; stop 1 tick beyond the defended level, 2R target, 1 micro",
        "verified": False,
        "status": "UNVERIFIED · PAPER ONLY",
        "win_pct": None,
        "profit_factor": None,
        "usd_per_trade": None,
        "trades_per_week": None,
        "held_out_trades": 0,
        "pro25k_pass_pct": None,
        "pro25k_bust_pct": None,
        "period": "NOT tested: no order-flow backtest exists (tick data unavailable, session 18). TradingView volume "
        "delta is an approximation of real bid/ask order flow.",
        "note": "Default OFF. Needs the 'Paytience Order Flow' alert on a 1-minute MNQ1! chart. The app rebuilds stop "
        "and target itself (never trusts the alert's prices); window, news, hedge lock, DLL, consistency and flat "
        "times all still apply. Never sends an order to a non-paper account.",
    },
]
