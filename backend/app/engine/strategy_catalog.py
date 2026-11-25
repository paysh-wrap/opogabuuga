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
    {
        "key": "jj_fpt",
        "name": "JJ F.P.T STRAT",
        "source": "JJ's Fair Pricing Theory, built only from his four videos (docs/JJ_FPT_RULES.md): the session open "
        "is the fair price; 5-minute opening continuation, then 85 minutes of displacement / break-of-structure "
        "entries back toward fair; 25 pt stop / 38 pt target (1 : 1.5)",
        "verified": False,
        "status": "UNVERIFIED",
        "win_pct": None,
        "profit_factor": None,
        "usd_per_trade": None,
        "trades_per_week": None,
        "held_out_trades": 0,
        "pro25k_pass_pct": None,
        "pro25k_bust_pct": None,
        "period": "Our 5-year MNQ test (docs/results/jj_fpt/RESULTS.md, 1 micro, costs in): win 37.7%, PF 0.86, "
        "negative every year; Pro evals almost never pass. JJ claims 57.5% win over 80 trades in 8 days "
        "(break-even is about 41%).",
        "note": "Default OFF. MNQ, New York 09:30–11:00 (plus the 08:30 news reversion on red-folder days). Every "
        "trade goes to ONE free account (no copy trading); size = 25% of that account's drawdown, same dollars on "
        "every stop. Funded / live accounts take break-of-structure entries only. All Lucid rules and Paytience "
        "safety checks still apply.",
    },
    {
        "key": "gala_pa",
        "name": "GALA PRICE ACTION",
        "source": "Gala Trades price action, built only from one transcript (docs/GALA_RULES.md): hourly trend from "
        "highs and lows, hourly body-pivot levels, then a 5-minute break-and-retest, bounce or rejection at the level; "
        "stop past the wick, target 2R",
        "verified": False,
        "status": "UNVERIFIED",
        "win_pct": None,
        "profit_factor": None,
        "usd_per_trade": None,
        "trades_per_week": None,
        "held_out_trades": 0,
        "pro25k_pass_pct": None,
        "pro25k_bust_pct": None,
        "period": "Not back-tested yet.",
        "note": "Default OFF. MNQ, entries 09:35–12:30 ET (D153). One free account per trade (no copy trading); "
        "size fits Lucid's DLL, MLL and consistency for 3 losses a day. With 2+ micros about half comes off at 2R "
        "and the rest runs with its stop moved to each closed 5-minute candle's open until it is above entry (D4/D5, "
        "D152); 1 micro exits all at 2R. All Lucid rules and Paytience safety checks still apply.",
    },
    {
        "key": "conti_orb",
        "name": "CONTI ORB",
        "source": "Matteo Conti's opening range breakout, built only from one transcript (docs/CONTI_RULES.md B): "
        "LONG on a close above the 09:30–10:00 high, stop at the range low, 1R or 2R, flat 15:30",
        "verified": False,
        "status": "UNVERIFIED",
        "win_pct": None,
        "profit_factor": None,
        "usd_per_trade": None,
        "trades_per_week": None,
        "held_out_trades": 0,
        "pro25k_pass_pct": None,
        "pro25k_bust_pct": None,
        "period": "Not back-tested yet.",
        "note": "Default OFF. MNQ, one trade a day. Same dollars at risk every trade (fewer micros on a wide range), "
        "fitted to Lucid's DLL, MLL and consistency. All Lucid rules and Paytience safety checks still apply.",
    },
    {
        "key": "conti_vwap",
        "name": "CONTI VWAP",
        "source": "Matteo Conti's VWAP idea, built only from one transcript (docs/CONTI_RULES.md C): 1-minute close "
        "above the 09:30 VWAP = long, below = short, out when price closes back through VWAP",
        "verified": False,
        "status": "UNVERIFIED",
        "win_pct": None,
        "profit_factor": None,
        "usd_per_trade": None,
        "trades_per_week": None,
        "held_out_trades": 0,
        "pro25k_pass_pct": None,
        "pro25k_bust_pct": None,
        "period": "Not back-tested yet.",
        "note": "Default OFF. MNQ 09:30–15:30. 25 pt emergency stop (not from the video). Max 3 losses a day for "
        "Lucid sizing. A reversal waits until the old position is flat. All Lucid rules and checks apply.",
    },
    {
        "key": "okala_8020",
        "name": "OKALA 8020",
        "source": "Okala's NASDAQ 80/20 levels, built only from one transcript (docs/OKALA_8020_RULES.md): level "
        "reactions, fork / reverse fork, cross-section entries; 10 pt stop, TP1 15 pt, then break even and a runner",
        "verified": False,
        "status": "UNVERIFIED",
        "win_pct": None,
        "profit_factor": None,
        "usd_per_trade": None,
        "trades_per_week": None,
        "held_out_trades": 0,
        "pro25k_pass_pct": None,
        "pro25k_bust_pct": None,
        "period": "Not back-tested yet. Okala claims a 70%+ win rate.",
        "note": "Default OFF. MNQ 09:30–11:30. Entries on 3-minute bars (his 200-second chart cannot be built from "
        "1-minute data). The ONLY strategy allowed to add to a winner (D145: same side, stop at break even, inside "
        "one trade's risk cap). All Lucid rules and Paytience safety checks still apply.",
    },
    {
        "key": "bruni_structure",
        "name": "BRUNI STRUCTURE",
        "source": "Gianluca Bruni's statistical structure model, built only from one transcript (docs/BRUNI_RULES.md): "
        "15-minute actual / peripheral structure, directional potential, triple-print zones, fixed 2R target",
        "verified": False,
        "status": "UNVERIFIED",
        "win_pct": None,
        "profit_factor": None,
        "usd_per_trade": None,
        "trades_per_week": None,
        "held_out_trades": 0,
        "pro25k_pass_pct": None,
        "pro25k_bust_pct": None,
        "period": "Not back-tested yet.",
        "note": "Default OFF. MNQ, New York session only. The video never shows the entry trigger: the built trigger "
        "(price back in the zone) is a flagged gap. Risk overlays (autocorrelation, regime flip, drawdown shield) are "
        "OFF and can only make trades smaller or fewer. All Lucid rules and safety checks still apply.",
    },
    {
        "key": "candace_ict",
        "name": "CANDACE ICT SCALP",
        "source": "Candace Lau's ICT scalp, built only from one transcript (docs/CANDACE_ICT_RULES.md): liquidity "
        "sweep, inverted FVG with displacement, retrace entry, stop past the sweep, ≥ 1:2 to the nearest pool",
        "verified": False,
        "status": "UNVERIFIED",
        "win_pct": None,
        "profit_factor": None,
        "usd_per_trade": None,
        "trades_per_week": None,
        "held_out_trades": 0,
        "pro25k_pass_pct": None,
        "pro25k_bust_pct": None,
        "period": "Not back-tested yet. London, the seconds charts and the Asia range cannot be tested here.",
        "note": "Default OFF. MNQ, New York 09:00–10:00 (London OFF). Every sweep is followed on its own (D154: a "
        "later sweep no longer replaces a pending setup). Grades A+ / B / C only shrink the Lucid-fit size. Single "
        "bracket (her partial and break-even move are not built). All Lucid rules and checks apply.",
    },
    {
        "key": "mgc_noise_candace",
        "name": "NOISE + CANDACE · MGC",
        "source": "D165: the same NOISE (noise-area momentum) and CANDACE ICT engines as the MNQ cards, run on MGC "
        "gold; parameters from a 30-day Yahoo (yfinance / OpenBB) test, docs/results/yf30/RESULTS.md",
        "verified": False,
        "status": "UNVERIFIED",
        "badge": "UNVERIFIED · 30-day yfinance test only",
        "win_pct": None,
        "profit_factor": None,
        "usd_per_trade": None,
        "trades_per_week": None,
        "held_out_trades": 0,
        "pro25k_pass_pct": None,
        "pro25k_bust_pct": None,
        "period": "30 days of Yahoo 2-minute continuous MGC=F (23 sessions, 2026-10-20 → 11-20), 1 micro, costs "
        "included, nothing held out. Far too small to show an edge.",
        "note": "Default OFF. Result at 1 micro: CANDACE 25 trades, win 48 %, PF 1.97, +$458 (random direction "
        "beats it 6 % of the time; picked from 8 settings, in-sample); NOISE only 2 trades (+$423) because "
        "10 sessions are warm-up. Same window MNQ: NOISE 10 trades PF 2.19, CANDACE 14 trades PF 2.04. "
        "Gold fell 12 % in the window and Yahoo splices contracts (not MGC.v.0), so treat all of it as a "
        "guess. MGC is the METALS group; fixed 1 micro; every Lucid rule and safety check still applies. "
        "Needs 10 stored MGC sessions from the feed.",
        "setting_key": "strategy.mgc_noise_candace",
        "addon": True,  # D184: runs BESIDE the main MNQ strategy (not one of the one-at-a-time choices)
        "addon_title": "Also trade MGC (NOISE + CANDACE on micro gold)",
        "addon_sizes": "MGC 1/1/1 · MNQ 4/4/4",
    },
    {
        "key": "order_flow_auction",
        "name": "ORDER FLOW · AUCTION (IMRE)",
        "source": "Imre Gans' auction-market theory, built only from one transcript (docs/IMRE_AMT_RULES.md): daily "
        "one-time-framing regime, prior-session value area, failed auctions in balance, micro-range breakouts in "
        "imbalance, big delta bubbles",
        "verified": False,
        "status": "UNVERIFIED",
        "win_pct": None,
        "profit_factor": None,
        "usd_per_trade": None,
        "trades_per_week": None,
        "held_out_trades": 0,
        "pro25k_pass_pct": None,
        "pro25k_bust_pct": None,
        "period": "Not back-tested yet. Delta is ESTIMATED from 1-minute bars; no DOM / heatmap data.",
        "note": "Default OFF. An Order Flow option (turns Order Flow on with it). MNQ 09:30–11:30, max 3 trades a day. "
        "All Lucid rules and Paytience safety checks still apply.",
        "setting_key": "strategy.order_flow_cfg.auction.enabled",
        "also": ["strategy.order_flow"],
    },
]
