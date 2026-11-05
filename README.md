# Paytience

Automated confluence trading app for 1–5 Lucid Trading LucidDaily 25K accounts (MNQ core; MES / MYM / MGC gated).
Signals come **only** from TradingView webhooks. Orders go **only** through the broker connection. The app never logs
into, scrapes, or clicks around TradingView or Lucid.

> **Status: Phase 2 of 11** — webhook receiver, TradingView bridge script, Python indicators, parity checker
> (+ Phase 1: config, database, audit log, login, Connections page, TradingAgents). **No trading decisions yet.** Default mode is PAPER. Do not connect funded accounts until the Live-Readiness Checklist passes.

## Quick start (your computer)

Prerequisites: Python 3.11+, Node 22, git.

```bash
make install
```

```bash
make keys >> .env
```

```bash
make create-admin
```

```bash
make build
```

```bash
make dev
```

Open http://127.0.0.1:8000, sign in as `admin`, and go to **Connections**. Every service shows where to log in or get
a key. Paste a key, press **Save & Test**, and the card turns gold when the live test passes.

Docker instead: `cp .env.example .env`, fill keys (`make keys`), then `make up` and run `make create-admin` once.

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
2. TradingView → open an **MNQ1!** chart: **1-minute** for profile TIGHT, **5-minute** for STD (one chart per profile).
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
- Every `# VERIFY` value in `config/rules/lucid_daily_25k.yaml` must be checked against your Lucid dashboard.
- Trading futures risks loss of capital. Paper-trade first.

## Development
`make test` · `make lint` · `make typecheck` · `E2E_PASSWORD=… make e2e` · `make check`
Spec: CLAUDE.md (condensed) · docs/DECISIONS.md (your changes) · docs/IMPROVEMENTS.md (proposals awaiting approval).
