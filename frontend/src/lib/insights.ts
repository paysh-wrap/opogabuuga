// Pure helpers for the §24 UI additions (no I/O).

const SKIP_LABELS: Record<string, string> = {
  RR_BELOW_MIN: "Reward:risk below minimum",
  RR_ABOVE_MAX: "Reward:risk above maximum",
  C1_TOO_SMALL: "C1 candle too small",
  OUTSIDE_WINDOW: "Outside trading hours",
  HEDGE_LOCK: "Hedge lock",
  NEUTRAL_SCORE_LOW: "Neutral bias and score too low",
  SCORE_LOW: "Score below minimum",
  MODEL_FAILED: "Setup failed before entry",
  COOLDOWN: "Cooling down after failed setups",
  STOP_TOO_TIGHT: "Stop too tight",
  STOP_TOO_WIDE: "Stop too wide for the risk budget",
  STOP_INVALID: "Stop on the wrong side",
  OPPOSING_DIVERGENCE: "Opposing divergence",
  BIAS_NO_TRADE: "No daily bias",
  CONSISTENCY_CAP: "Consistency cap",
  UNKNOWN: "No reason recorded",
};

/** Plain-English label for a skip code; unknown codes are shown as-is. */
export function skipLabel(code: string): string {
  if (SKIP_LABELS[code]) return SKIP_LABELS[code];
  if (code.startsWith("NEWS")) return "News blackout";
  return code;
}

export interface SkipRow { code: string; label: string; count: number; avg: number }

/** Merge today's counts with the 20-session average, biggest first. */
export function skipRows(counts: Record<string, number>, avg: Record<string, number>): SkipRow[] {
  return Object.keys(counts)
    .map((code) => ({ code, label: skipLabel(code), count: counts[code] ?? 0, avg: avg[code] ?? 0 }))
    .sort((a, b) => b.count - a.count || a.code.localeCompare(b.code));
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
