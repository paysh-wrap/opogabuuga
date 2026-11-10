# Paytience

Automated confluence trading app for 1–5 Lucid Trading (Pro/Flex) accounts on **Micro Gold (MGC) and Micro Nasdaq
(MNQ)** futures (max 3 trades/day per account). Signals come **only** from TradingView webhooks. Orders go **only** through the
broker connection. The app never logs into, scrapes, or clicks around TradingView or Lucid.

> **Status: complete and running in PAPER mode by default.** Strategy, risk engine (every Lucid rule checked before
> each order), automation (OFF / SEMI / FULL), payouts, Strategy Lab, backtests and the full UI are built and tested
> (545+ backend tests, 52 UI tests, browser E2E). **Main strategy:** trend-aligned 1.5–2.5R — see
> [docs/STRATEGY_MAIN.md](docs/STRATEGY_MAIN.md). **Needs from you before it trades:** an Anthropic API key for
> TradingAgents (Connections page; no key = no trades), your broker connection, and the `# VERIFY` values checked
> against your Lucid dashboard. LIVE trading stays locked until the Live-Readiness Checklist passes.

## Quick start (your computer) — one click

Install once: **Python 3.11+** (python.org) and **Node.js LTS** (nodejs.org). Then:

- **Mac:** double-click **`start.command`** (first time: right-click → Open).
- **Windows:** double-click **`start.bat`**.
- **Any computer:** `python3 start.py` (or `make start`).

The first run installs everything, creates your secret keys (`.env`, keep it private), sets up the database, asks
once for your dashboard password (user name **PayDay**), installs TradingAgents and builds the dashboard (a few
minutes). After that it just starts and opens your browser at http://127.0.0.1:8000. Close the window or press
Ctrl+C to stop.

Manual steps instead (developers): `make install`, `make keys >> .env`, `make create-admin`, `make build`, `make dev`.

Open http://127.0.0.1:8000, sign in as `PayDay`, and go to **Connections**. Every service shows where to log in or get
a key. Paste a key, press **Save & Test**, and the card turns gold when the live test passes.

Docker instead: `cp .env.example .env`, fill keys (`make keys`), then `make up` and run `make create-admin` once.

## Use it on your phone (mobile app)

Paytience installs on your phone like an app (home-screen icon, full screen, no browser bars):
1. On your computer start it with **`python3 start.py --phone`** (Mac/Windows: run that in a terminal in this folder).
   It prints an address like `http://192.168.1.20:8000`.
2. On your phone (same Wi-Fi) open that address and sign in.
3. **iPhone:** Share → **Add to Home Screen**. **Android:** ⋮ menu → **Install app** / **Add to Home screen**.

The computer must stay on with Paytience running (it does the trading; the phone is the remote control).
Away from home: use a Cloudflare Tunnel (below) and open your tunnel address on the phone instead. Only use
`--phone` on your own home Wi-Fi.

## API keys (Connections page)
- **TradingAgents (required — the backbone):** Connections → TradingAgents → pick the LLM provider (e.g. Anthropic),
  paste your API key → **Save & Test**. Without it the daily bias is NO_TRADE and nothing trades.
- **OpenBB (optional):** Connections → OpenBB → optional OpenBB Hub token / FMP / Polygon keys. The free Yahoo feed
  works without keys; OpenBB is information only (never places or blocks trades).
- Broker (CrossTrade), Databento (backtest data), Telegram/Discord alerts: same page.

## Connections page
- Keys are encrypted with your `PAYTIENCE_MASTER_KEY` (Fernet), never shown again (last 4 chars only), never logged.
- Tests are read-only: they never place orders or send messages. Broker relays that can't be tested show **Saved**.
- Updates appear live in every open tab (WebSocket).
- Lose the master key = re-enter all keys (they can't be decrypted).

## TradingAgents (AI bias)
[TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) **v0.7.1**
(commit `3e44faafa042daf953f6ec2422ae36bb1fd4f50f`, Apache-2.0) is installed by `make tradingagents` into its own
virtualenv `.venv-ta`. The app talks to it through a subprocess with a hard timeout, so it can never block trading.
Ratings map Buy/Overweight → LONG_ONLY, Hold → NEUTRAL, Underweight/Sell → SHORT_ONLY; anything else
(including `REVIEW`) → NO_TRADE + alert. Until you add an LLM key, bias is NO_TRADE and no trades are taken.

## Indicators — PERSONAL USE ONLY where licensed so
- "ICT Fractal Model, HTF Candles, CISD & C2 Targets [LunqFX]" — © LunqFX
- "Market Structure Oscillator [BigBeluga]" — © BigBeluga
Paste each script's source + license on the Connections page. The app records the license; non-commercial
licenses mean this project is for personal use only.

## TradingView alert setup (step by step)
1. Connections page → **TradingView setup** → download `Paytience_Bridge.pine`.
2. TradingView → open **MGC1!** (Micro Gold) and **MNQ1!** (Micro Nasdaq) charts: **1-minute** for profile
   TIGHT, **5-minute** for STD (one chart + one alert per market per profile = 4 alerts).
3. Pine Editor → paste the script → **Add to chart**.
4. Indicator settings → paste the **Webhook secret** (Connections page → Reveal) → choose the profile.
5. Create alert → Condition **Paytience_Bridge** → **Any alert() function call** → Expiration open-ended →
   Notifications → **Webhook URL** = the URL shown on the Connections page.
6. Within one bar the **Live feeds** list shows the symbol as Fresh and the TradingView card turns gold.
   If not, the rejection counter on the same page says why (bad secret, wrong chart timeframe, stale, …).

The bridge is Paytience's own implementation of docs/INDICATOR_SPEC.md (spec-derived). It has not yet been verified
against the original LunqFX/BigBeluga source; LIVE stays blocked until parity passes over ≥ 20 sessions.

## Exposing the webhook (TradingView → your app)
TradingView only posts to HTTPS on port 443. Use a Cloudflare Tunnel to `http://127.0.0.1:8000`; a VPN alone
does not make the app reachable. Recommended: protect the dashboard with Cloudflare Access and expose only
`/api/webhook/*`. Then set `PAYTIENCE_COOKIE_SECURE=true`.

## Warnings
- **Hedging:** positions at other firms/platforms are invisible to this app. Opposite correlated positions elsewhere
  can count as hedging under Lucid rules. You must attest each session that you hold none.
- Every `# VERIFY` value in your plan file (`config/rules/lucid_{pro,flex}_<size>k.yaml`, picked on the Risk page)
  must be checked against your Lucid dashboard.
- Trading futures risks loss of capital. Paper-trade first.

## Development
`make test` · `make lint` · `make typecheck` · `make e2e` (scratch DB) · `E2E_PASSWORD=… make e2e-live` · `make check`
Spec: CLAUDE.md (condensed) · docs/DECISIONS.md (your changes) · docs/IMPROVEMENTS.md (proposals awaiting approval).
