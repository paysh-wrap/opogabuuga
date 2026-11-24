// Pure helpers for the §24 UI additions (no I/O).

const SKIP_LABELS: Record<string, string> = {
  // confluence / trade-plan gates
  RR_BELOW_MIN: "Reward:risk below minimum",
  RR_BELOW_MIN_AFTER_ROUNDING: "Reward:risk fell below minimum after tick rounding",
  RR_ABOVE_MAX: "Reward:risk above maximum",
  RR_INVALID_AFTER_FILL: "Reward:risk invalid after the fill",
  C1_TOO_SMALL: "C1 candle too small",
  C1_SWEPT: "C1 range already swept",
  OUTSIDE_WINDOW: "Outside trading hours",
  HEDGE_LOCK: "Hedge lock (opposite direction already open)",
  NEUTRAL_SCORE_LOW: "Neutral bias and score too low",
  SCORE_LOW: "Score below minimum",
  SCORE_BELOW_MIN: "Score below minimum",
  MODEL_FAILED: "Setup failed before entry",
  MODEL_ALREADY_TRADED: "This setup was already traded",
  MODEL_NOT_CONFIRMED: "Setup not confirmed yet",
  COOLDOWN: "Cooling down after failed setups",
  STOP_TOO_TIGHT: "Stop too tight",
  STOP_TOO_WIDE: "Stop too wide for the risk budget",
  STOP_INVALID: "Stop on the wrong side",
  OPPOSING_DIVERGENCE: "Opposing divergence",
  BIAS_NO_TRADE: "No daily bias",
  NO_TRADE: "No trade today",
  // risk / account / firm rules
  CONSISTENCY_CAP: "Consistency cap",
  CONSISTENCY_DAY_STOP: "Consistency day stop reached — no new entries today",
  DAY_STOP: "Day stop reached",
  DLL_LIMIT: "Daily loss limit too close",
  NEAR_MLL: "Too close to the max loss limit",
  DRAWDOWN_TOO_DEEP: "Drawdown too deep",
  CONSECUTIVE_LOSSES: "Too many losses in a row",
  MAX_TRADES: "Max trades for the day reached",
  CUSHION_MAX_TRADES: "Cushion level allows no more trades today",
  CUSHION_STOP: "Cushion too low to trade",
  RISK_BASE_BELOW_PAUSE: "Account paused: risk base below the floor",
  AGGREGATE_RISK_EXCEEDS_LIMITS: "Combined risk over the account limits",
  WORST_CASE_EXCEEDS_LIMITS: "Worst case over the account limits",
  SPLIT_BUDGET_EXCEEDED: "Split risk budget used up",
  FAST_EVAL_QUALITY_DAY: "Fast evaluation: not a quality day",
  PAYOUT_PENDING: "Payout pending — trading blocked",
  ATTESTATION_MISSING: "Positions attestation missing",
  CALENDAR_MISSING: "Economic calendar missing",
  ACCOUNT_NOT_READY: "Account not ready",
  ACCOUNT_PAUSED: "Account paused",
  POSITION_OPEN: "A position is already open",
  PROFILE_DISABLED: "Profile switched off",
  INSTRUMENT_DISABLED: "Instrument switched off",
  MODE_OFF: "Automation is OFF",
  HARD_FLAT: "Hard flat time reached",
  LAST_MINUTES: "Too close to the flat time",
  // data / feed / news
  FEED_DELAYED: "Price feed delayed (not real time)",
  FEED_STALE: "Price feed stale",
  FEED_GAP: "Gap in the price feed",
  FEED_LOST: "Price feed lost",
  NEWS_BLACKOUT: "News blackout",
  NEWS_FLATTEN: "News flatten window",
  NO_HISTORY: "Not enough price history",
  TREND_WARMUP: "Trend filter still warming up",
  // late-day / advisor / AI
  LATE_DAY_NOT_ACTIVE: "Late-day option not active for this account",
  ADVISOR_DISAGREE: "AI advisor disagrees",
  ADVISORY_NO_AGREEMENT: "AI advisor gave no agreement",
  AI_DISAGREE: "AI call disagrees",
  AI_MISSING: "No AI call today",
  AI_TA_MISSING: "TradingAgents call missing",
  AI_VT_MISSING: "Vibe-Trading call missing",
  AI_NEUTRAL: "AI call is neutral",
  AI_NOT_STRONG: "AI call not strong enough",
  RESEARCH_FAILED: "Research run failed",
  RESEARCH_NO_TRADE: "Research says no trade",
  SIGNAL_NOT_TRADEABLE: "Signal not tradeable",
  // rule-sheet strategies
  BIG_OPEN: "Opening move too big",
  DEAD_ZONE: "Dead zone (no edge)",
  LONG_ONLY: "Only longs allowed today",
  SHORT_ONLY: "Only shorts allowed today",
  NOT_A_PLUS: "Not an A+ setup",
  PROGRAM_DAY: "Program day — no entries",
  SMALL_ROOM: "Not enough room to the target",
  TARGET_TOO_CLOSE: "Target too close",
  TREND_AGAINST: "Against the trend",
  WAIT_FOR_LARGER: "Waiting for a larger move",
  WOULD_BREAK_BUFFER: "Would break the risk buffer",
  BRUNI_NO_BARS: "BRUNI: no bars to read",
  CORB_NO_BARS: "Opening range: no bars",
  CORB_NO_RANGE: "Opening range: no range yet",
  GALA_NO_BARS: "GALA: no bars to read",
  GALA_NO_LEVEL: "GALA: no level to trade",
  GALA_NO_OPEN: "GALA: no opening price",
  GALA_NO_TREND: "GALA: no clear trend",
  GALA_NEWS_FIRST_HOUR: "GALA: news in the first hour",
  OKALA_ADD_CAP: "OKALA: add would exceed the risk cap",
  OKALA_ADD_NOT_AT_BE: "OKALA: stop not at break even yet",
  OKALA_ADD_OPPOSITE: "OKALA: add is the opposite direction",
  OKALA_MAX_ADDS: "OKALA: maximum adds reached",
  SETUP_CONF_LOW: "Research setup confidence too low",
  SETUP_EXPIRED: "Research setup expired",
  SETUP_INVALIDATED: "Research setup invalidated",
  SETUP_LEVELS_INVALID: "Research setup levels invalid",
  SETUP_MALFORMED: "Research setup unreadable",
  SETUP_ZONE_INVALID: "Research setup zone invalid",
  // order flow
  OF_BAD_PRICE: "Order Flow: bad price",
  OF_COMPRESSION: "Order Flow: compression (no movement)",
  OF_DAILY_CAP: "Order Flow: daily trade cap reached",
  OF_DELTA_ESTIMATED: "Order Flow: delta is only estimated",
  OF_ENVIRONMENT: "Order Flow: market environment not suitable",
  OF_LEVEL_WRONG_SIDE: "Order Flow: level on the wrong side",
  OF_LOCATION: "Order Flow: price not at a good location",
  OF_NO_CONFIRM: "Order Flow: no confirmation",
  OF_PATH_EXHAUSTED: "Order Flow: path already used up",
  OF_PATH_UNKNOWN: "Order Flow: path unknown",
  OF_POSITION_OPEN: "Order Flow: position already open",
  OF_TA_ADVICE: "Order Flow: AI advice against",
  OF_TA_DISAGREES: "Order Flow: AI call disagrees",
  OF_UNKNOWN_SIGNAL: "Order Flow: unknown signal",
  OF_ZONE_EXCLUSIVE: "Order Flow zones: another zone strategy is active",
};

/** Prefix rules for families of codes (checked after the exact list). */
const SKIP_PREFIX_LABELS: [string, string][] = [
  ["NEWS", "News blackout"],
  ["OF_AMT_", "AMT+ Order Flow filter"],
  ["OF_ZONE_", "Order Flow zone filter"],
  ["OF_CASPER_", "Order Flow Casper filter"],
  ["OF_", "Order Flow filter"],
];

/** "SOME_UNLISTED_CODE" -> "Some unlisted code": never show a bare code. */
function humanize(code: string): string {
  const t = code.toLowerCase().replace(/_+/g, " ").trim();
  return t ? t.charAt(0).toUpperCase() + t.slice(1) : code;
}

/** Plain-English label for a skip code. Every code gets words; the exact list wins, then prefix families, then a readable fallback. */
export function skipLabel(code: string): string {
  if (SKIP_LABELS[code]) return SKIP_LABELS[code];
  const fam = SKIP_PREFIX_LABELS.find(([p]) => code.startsWith(p));
  if (fam) return code.startsWith("OF_") ? `${fam[1]}: ${humanize(code.replace(/^OF_(AMT_|ZONE_|CASPER_)?/, ""))}` : fam[1];
  return humanize(code);
}

/** Which strategy a skip code belongs to (shared codes -> "Any strategy"). Used to group the Why-no-trade table. */
export function skipStrategy(code: string): string {
  if (code.startsWith("OF_")) return "Order Flow";
  if (code.startsWith("GALA_")) return "GALA";
  if (code.startsWith("OKALA_")) return "OKALA";
  if (code.startsWith("BRUNI_")) return "BRUNI";
  if (code.startsWith("CORB_") || code.startsWith("CONTI_")) return "CONTI";
  if (code.startsWith("LATE_DAY")) return "Late-day option";
  if (code.startsWith("AI_") || code.startsWith("ADVISOR") || code.startsWith("ADVISORY") || code.startsWith("RESEARCH_") || code.startsWith("SETUP_")) return "AI advisor / research";
  if (["RR_BELOW_MIN", "RR_BELOW_MIN_AFTER_ROUNDING", "RR_ABOVE_MAX", "RR_INVALID_AFTER_FILL", "C1_TOO_SMALL", "C1_SWEPT", "NEUTRAL_SCORE_LOW", "SCORE_LOW", "SCORE_BELOW_MIN", "MODEL_FAILED", "MODEL_ALREADY_TRADED", "MODEL_NOT_CONFIRMED", "OPPOSING_DIVERGENCE", "BIAS_NO_TRADE"].includes(code)) return "Confluence model";
  if (["BIG_OPEN", "DEAD_ZONE", "LONG_ONLY", "SHORT_ONLY", "NOT_A_PLUS", "PROGRAM_DAY", "SMALL_ROOM", "TARGET_TOO_CLOSE", "TREND_AGAINST", "WAIT_FOR_LARGER", "WOULD_BREAK_BUFFER"].includes(code)) return "Rule-sheet strategies";
  return "Any strategy";
}

export interface SkipRow { code: string; label: string; count: number; avg: number; strategy: string }

/** Merge today's counts with the 20-session average, biggest first. */
export function skipRows(counts: Record<string, number>, avg: Record<string, number>): SkipRow[] {
  return Object.keys(counts)
    .map((code) => ({ code, label: skipLabel(code), count: counts[code] ?? 0, avg: avg[code] ?? 0, strategy: skipStrategy(code) }))
    .sort((a, b) => b.count - a.count || a.code.localeCompare(b.code));
}

/** Group skip rows by strategy; the biggest strategy (by skips today) first, "Any strategy" last. */
export function groupSkips(rows: SkipRow[]): { strategy: string; total: number; rows: SkipRow[] }[] {
  const m = new Map<string, SkipRow[]>();
  rows.forEach((r) => m.set(r.strategy, [...(m.get(r.strategy) ?? []), r]));
  return [...m.entries()]
    .map(([strategy, rs]) => ({ strategy, total: rs.reduce((a, r) => a + r.count, 0), rows: rs }))
    .sort((a, b) => (a.strategy === "Any strategy" ? 1 : b.strategy === "Any strategy" ? -1 : b.total - a.total || a.strategy.localeCompare(b.strategy)));
}

export type Band = "safe" | "warn" | "danger";

/** Blue below 50% used, gold from 50%, small red badge from 80%. */
export function band(used: number): Band {
  return used >= 0.8 ? "danger" : used >= 0.5 ? "warn" : "safe";
}

const clamp = (x: number) => (Number.isFinite(x) ? Math.min(1, Math.max(0, x)) : 0);

export interface MeterSpec { key: string; label: string; used: number; detail: string }

export interface MeterAcct {
  stage: string; to_mll?: string | null; max_loss?: string; dll_left?: string | null; dll_limit?: string | null;
  consistency_cap?: string | null; today_pnl?: string; idle_days?: number; idle_delete_days?: number;
}

const usd = (n: number) => `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;

/** Rule-proximity meters (§24.5). `used` is 0..1 of the allowed room. */
export function meters(a: MeterAcct): MeterSpec[] {
  const out: MeterSpec[] = [];
  const maxLoss = Number(a.max_loss);
  if (a.to_mll != null && maxLoss > 0)
    out.push({ key: "mll", label: "MLL distance", used: clamp(1 - Number(a.to_mll) / maxLoss), detail: `${usd(Number(a.to_mll))} left of ${usd(maxLoss)}` });
  const dll = Number(a.dll_limit);
  if (a.dll_left != null && dll > 0)
    out.push({ key: "dll", label: "DLL used", used: clamp(1 - Number(a.dll_left) / dll), detail: `${usd(Number(a.dll_left))} left of ${usd(dll)}` });
  const cap = Number(a.consistency_cap);
  if (a.stage === "EVAL" && a.consistency_cap != null && cap > 0) {
    const today = Number(a.today_pnl ?? 0);
    out.push({ key: "cons", label: "Consistency headroom", used: clamp(today / cap), detail: `${usd(Math.max(cap - today, 0))} of ${usd(cap)} cap left today` });
  }
  const del = Number(a.idle_delete_days);
  if (a.idle_days != null && del > 0)
    out.push({ key: "idle", label: "Days since last trade", used: clamp(a.idle_days / del), detail: `${a.idle_days} of ${del} days` });
  return out;
}

export interface DayPnl { date: string; pnl: string }

/** Monday-first week grid for a daily P&L series: each week has 5 trading cells (Mon-Fri) + weekend cells folded in. */
export interface CalWeek { start: string; days: (DayPnl | null)[]; total: number }

function addDays(iso: string, n: number): string {
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}
function weekStart(iso: string): string {
  const dow = (new Date(iso + "T00:00:00Z").getUTCDay() + 6) % 7; // Monday = 0
  return addDays(iso, -dow);
}

export function calendarWeeks(days: DayPnl[]): CalWeek[] {
  const by = new Map(days.map((d) => [d.date, d]));
  const starts = [...new Set(days.map((d) => weekStart(d.date)))].sort();
  return starts.map((start) => {
    const cells = Array.from({ length: 7 }, (_, i) => by.get(addDays(start, i)) ?? null);
    return { start, days: cells, total: cells.reduce((s, c) => s + Number(c?.pnl ?? 0), 0) };
  });
}

export function signedUsd(n: number): string {
  return `${n > 0 ? "▲ +" : n < 0 ? "▼ −" : ""}$${Math.abs(n).toFixed(2)}`;
}
