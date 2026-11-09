"""D55: research results shown next to each strategy button (static facts from the session 9 study — NOT live data).

Source: docs/results/2026-11-09_session9_strategy_research.md (Databento MNQ 1-minute 2019-05 → 2026-11, pick on
2019–2023, judge unchanged on 2024-01 → 2026-11, 1 micro, costs included). Pro 25K figures: tools/sim25k.py rolling
starts on real held-out days (eval: +$1,250 target, $1,000 EOD trailing max loss; open-trade drawdown and news not
modeled → somewhat optimistic). The LunqFX row is the engine's own 1-year run (D52/D54)."""

from __future__ import annotations

CATALOG: list[dict[str, object]] = [
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
        "source": "ICT/LunqFX C1→C2 sweep + CISD, BigBeluga MSO (D49–D54)",
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
        "note": "No credible independent evidence for sweep/CISD setups; kept as a button. Off = runs in SHADOW.",
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
]
