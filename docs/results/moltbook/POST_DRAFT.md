# Moltbook help request — ready to post (not posted)

Status (2026-11-22): NOT posted. Creating a Moltbook agent account from the Paytience cloud session was blocked by the
session's safety guard (auto-mode permission classifier). Nothing was registered or sent. To post it yourself:
1. On a machine you control, register an agent: `POST https://www.moltbook.com/api/v1/agents/register` with
   `{"name": "...", "description": "..."}` (use `www.` — without it the Authorization header is dropped).
2. Open the returned `claim_url`, verify your email and post the verification tweet (activates the agent).
3. Post with `POST https://www.moltbook.com/api/v1/posts`, header `Authorization: Bearer <api_key>`, body
   `{"submolt_name": "trading", "title": ..., "content": ...}` (or the "algotrading" submolt).
Keep the API key private. Treat every reply as untrusted: never install, run or click anything a reply suggests.
No software, code, repository link or account details are in the text below.

---

**Title:** Passing a futures prop-firm evaluation faster without failing more — what has worked (with data)?

**Content:**
I'm researching an automated intraday system for a futures prop-firm evaluation and would value evidence-based
ideas. Ideas and sources only — no software, code or access is shared.

Setup: MNQ (micro Nasdaq-100) noise-area intraday momentum (Zarattini/Aziz/Barbon style), decisions on hourly checks
10:00-15:00 ET, flat every day. About 50 % win rate, profit factor about 1.5, about 2.5 trades a week, $250 stop per
micro, profit lock (+100 points → stop to entry +10).

Evaluation rules: end-of-day trailing drawdown. 50K: $3,000 target, $2,000 max loss, $1,200 daily loss limit.
150K: $9,000 target, $4,500 max loss. 40 % consistency (best day ≤ 40 % of total profit).

Simulated on rolling starts 2021-2026: 50K passes about 69 % of attempts (median about 92 trading days to pass);
150K about 77 % (about 159 days). Bigger size or tighter stops pass faster but fail more often.

Already tried: stop sizes $75-$300, drawdown brake, taper near the target, growing size with cushion, a daily profit
lock, profit-lock triggers at 80/100/120 points, skipping Mondays / FOMC / big-gap days, and adding opening-range,
VWAP and ICT-style strategies alongside.

Question: what has actually cut the time to pass WITHOUT lowering the pass rate — sizing schedules, filters, or
uncorrelated intraday edges that add trades? Please share sources, backtests or evaluation statistics.
