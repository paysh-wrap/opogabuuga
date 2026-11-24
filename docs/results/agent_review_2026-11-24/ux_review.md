# UX review: Strategy page and its links to Dashboard / Today (2026-11-24)

Read-only review. Evidence: source code, plus a real backend on a throwaway SQLite DB (Pro 25K plan, 2 EVAL accounts),
rendered at 1280 px and 390 px with Playwright. Error states were tested by forcing HTTP 500 / 422 on single endpoints.
Measured: Strategy page height **8,106 px desktop, 15,529 px at 390 px** (~18 phone screens). No horizontal scroll on any page.
All titles correct ("Paytience · <Page>").

## Ranked problems (by user impact)

### 1. Rejected saves fail silently (breaks "no silent failures")
- `frontend/src/components/StrategyButtons.tsx:148-188` (toggle, sbs, size, suggest, flip, lateFlip), `StrategyPresets.tsx:138-142`,
  `AdvisorCard.tsx:48-51`, `TrailCushionCard.tsx:44-48`, `FlagToggle.tsx:346-349`: mutations have `onSettled` only, no `onError`.
- Experience: forced a 422 on PUT /api/risk/settings, clicked a strategy button: **zero alerts on the page**; the button just
  snaps back. The user cannot tell "rejected by D167 / validation" from "network blip".
- Also `exNote` (line 155) is set *before* the request, so it can claim "X is now the only strategy ON" for a save that failed.
- Change: one shared hook, set the note only on success.
```tsx
const useSave = (label: string) => { const [err, setErr] = useState(""); const qc = useQueryClient();
  return { err, m: useMutation({ mutationFn: (body) => api("/api/risk/settings", {method:"PUT", body: JSON.stringify(body)}),
    onSuccess: () => setErr(""), onError: (e) => setErr(`${label} not saved: ${(e as Error).message}`),
    onSettled: () => qc.invalidateQueries({ queryKey: ["strategies"] }) }) }; };
{err && <p role="alert" className="text-goldLight">⚠ {err}</p>}
```

### 2. Failed loads spin forever / vanish (safety banner included)
- `pages/Strategy.tsx:28` and `StrategyButtons.tsx:190`: `if (!data) return Loading…` with no `error` branch. A 500 on
  /api/strategy showed "Loading…" indefinitely. Same in `pages/Today.tsx:216` (main), `:225` (plan panel just disappears),
  `WhyNoTrade.tsx:220`, `AiLedger.tsx:272`, `TrailCushionCard.tsx:50`; `StrategyPresets.tsx:144` and `AdvisorCard.tsx:53` return `null`.
- **Most serious:** `components/SafetyBanners.tsx:339-340` returns `null` when /api/safety fails. Forced 500: 0 alerts on Dashboard.
  The user sees "no problems" exactly when the app cannot check for problems.
- Change: `if (q.error) return <p role="alert">⚠ Cannot load safety status: {msg}. Treat as NOT safe; new entries may be blocked.</p>`
  in SafetyBanners; same pattern (already used in `StrategyGates.tsx:91`, `Dashboard.tsx:48`) everywhere above.

### 3. No single "what is ON" answer; nothing-ON state is invisible
- Strategy page opens with a note about CME volume (`Strategy.tsx:33`), then a long button list. There is no summary line.
  Dashboard (`Dashboard.tsx:57`) and Today show automation mode and bias but **never the active strategy**; header neither.
- Fresh DB default ON = `noise` + `pm_fade` (CANDACE off) although the section is titled "MAIN strategy — NOISE + CANDACE".
  Clicking "ON · NOISE" turned the whole main choice off: API then reported **no strategy ON**, and the page shows only blue
  "OFF ·" buttons with no warning that the app will not trade.
- Change: a sticky "Now running" strip at the top of Strategy, reused as a Dashboard tile and header chip:
```
┌ NOW RUNNING ───────────────────────────────────────────────┐
│ MAIN · NOISE + CANDACE (CANDACE off)  ·  Fast pass: 25K ✓ 50K – 100K – 150K – │
│ Safe today?  Pre-flight ✓ 09:25 · Calendar ✓ · Bias NEUTRAL · Feed FRESH      │
│ Last decision 10:42 NOISE SKIP · Consistency cap   [Why? →]                   │
└────────────────────────────────────────────────────────────┘
None ON → gold box: "No strategy is ON — Paytience will not open trades."
```
  Data already exists: /api/strategies (enabled), /api/today/plan (preflight, calendar), /api/strategy-gates (last).

### 4. D167 single-choice is explained in text, not in the control
- `StrategyButtons.tsx:377` hint is a small paragraph; buttons (`:202-210`) are independent `aria-pressed` toggles spread over
  three groups, one of them a closed `<details>` (`:394`). The exclusive note (`:376`) renders at the top of the section:
  turning GALA on from inside "Lesser strategies" (scrollY 2,844) the note was off-screen; the main buttons silently flipped.
- NOISE and CANDACE are one choice but two buttons: clicking either OFF only changes that one setting (`:159`), turning one ON
  turns both ON (`:157`). Users get half-states the heading does not describe.
- Change: make it a real radio group. One "MAIN · NOISE + CANDACE" card with `role="radio"`; CANDACE as a sub-switch inside it;
  every lesser/order-flow card gets the same radio. Render the confirmation next to the clicked card, and before switching
  ask inline: "Turn on GALA? This turns off MAIN (NOISE + CANDACE). [Switch] [Cancel]". Show the current choice on the
  closed "Lesser strategies" summary: `Lesser strategies (7) · none ON` / `· GALA ON`.

### 5. Skip reasons are hard to find and incomplete
- Dashboard puts WhyNoTrade (`Dashboard.tsx:68`) below bento, checklist, markets, plan, projection: ~3rd phone screen+.
- `lib/insights.ts:3-20` labels only 16 old confluence codes; strategy codes (CONSISTENCY_DAY_STOP, LATE_DAY_NOT_ACTIVE,
  SPLIT_BUDGET_EXCEEDED, ADVISOR_DISAGREE, FEED_DELAYED, HEDGE_LOCK variants, OF_AMT_*) show as raw codes.
- `WhyNoTrade` counts are not split by strategy; Order Flow skips live in AuditLog (`backend/app/api/strategy_gates.py:437-452`)
  and never reach /api/signals/skips (`backend/app/api/signals.py:89-110`), so the table can say "No skipped signals today"
  while Order Flow skipped.
- Today's Signals table (`Today.tsx:264`) prints `skip_reason` raw.
- Change: add `strategy` column and labels; one plain sentence first: "Last skip 10:42 · NOISE · Consistency day stop
  reached ($475 of $500) — no new NOISE entries today." Link each row to Strategy gates card `#sg-noise`.

### 6. Fast-pass cards: what the switch does is buried in one long button label
- `StrategyButtons.tsx:333-368`: title, weekly figures, then two buttons whose ON label is the whole size formula
  (backend `api/dashboard.py:1208-1222`, e.g. "NOISE 5 @ $100 stop (cushion < $2,250: 2, < $1,500: 1; +1 per $500 …) · CANDACE …").
  "Applies to EVAL only / which of my accounts" is hidden in More info. Nothing says whether any of the user's accounts is that size.
- Weekly figures: "needed" vs "simulated" are adjacent with no verdict; calculator sits above the cards (`:385`), so its
  numbers are read before the user knows what the plans are.
- Change per card:
```
25K FAST PASS (evaluations)            [ OFF | ON ]   applies to: E1, E2 (25K EVAL)  / "no 25K EVAL account"
What changes: NOISE 1 → 1 micro @ $75 stop · CANDACE 2 (1 below $333 cushion)
Pace: needs $1,106/wk · backtest avg $371/wk  → about 3× slower than the target pace   [NOT RE-MEASURED]
▸ Late-day 3rd edge (UNVERIFIED)  ▸ Details
```
  Move the calculator below the four cards.

### 7. UNVERIFIED labelling is inconsistent
- Late-day badge hard-coded "held-out PF 1.10" in the UI (`StrategyButtons.tsx:357`) **and** in the label (`api/dashboard.py:1194`),
  shown twice in one card; D166 and `app/config.py:963` / `engine/late_day.py:10` say **1.12**.
- "NOT RE-MEASURED after D163" is hard-coded text (`:340`); should come from the API `source`.
- Verified vs unverified on strategy cards is a red/green dot only (`:211`) plus a gold word; the gold UNVERIFIED pill
  appears only on some cards (order flow, rule-sheet strategies) and on Trail/Cushion; MGC (D165) relies on `s.badge`.
- Change: one `<EvidenceBadge verified source />` component placed next to the card title on every card; text from API only.

### 8. Page length and order on mobile
- 15.5k px at 390 px. After the strategy section come Presets, Advisor, Trail/Cushion, TA MGC, Trading-R1, Gates, AI ledger
  (twice: `StrategyButtons.tsx:467-475` and `<AiLedger/>` at `Strategy.tsx:41`), then TA/feed cards. "Gates per strategy"
  (the "why skipped" detail) is ~10 screens down. The 16-item nav strip (`Layout.tsx:99-116`) plus dock is fine.
- Trail/Cushion table lacks CANDACE (`TrailCushionCard.tsx:9-11`) though it is MAIN.
- Change: order = Now running → Main (+fast pass) → Gates for the ON strategy → Order Flow → Lesser (closed) → "Advanced"
  `<details>` containing presets, size tables, trail/cushion, advisor, AI ledger (once), research cards.

### 9. Colour rule nits (§18)
- `Strategy.tsx:19` dot uses grey `#64748B` and raw hex instead of `theme`/`badge`; `StrategyGates.tsx:21` and
  `Header.tsx:235` use raw hex too (values match `badge`, but bypass theme.ts). `WhyNoTrade.tsx:228` `opacity-60` text
  lowers contrast below AA risk. Otherwise text stays blue/gold, P&L uses ▲/▼ and sign.

## Ship-one-by-one list (priority order)
1. `onError` + `role="alert"` on every Strategy-page mutation; set the D167 note only on success (problem 1).
2. Error branch in SafetyBanners ("cannot check safety = treat as not safe") and in Strategy/Today/WhyNoTrade loaders (2).
3. "Now running" strip on Strategy + same tile on Dashboard; loud gold "No strategy ON" state (3).
4. Fold NOISE+CANDACE into one MAIN radio card with CANDACE sub-switch; inline confirm next to the clicked card; show
   current choice on the Lesser summary (4).
5. WhyNoTrade: strategy column, labels for all strategy skip codes, include Order Flow audit skips, move above the fold
   on Dashboard (5).
6. Fast-pass card rewrite: applies-to accounts line, short "what changes", pace verdict; calculator below cards (6).
7. Single EvidenceBadge from API data; fix PF 1.10 → 1.12 at the source (`api/dashboard.py:1194`), drop the duplicate
   UI badge (7).
8. Move secondary panels into an "Advanced" fold, remove the duplicate AI ledger, add CANDACE to Trail/Cushion (8).
