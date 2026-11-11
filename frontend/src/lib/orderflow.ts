// D98 Order Flow chart — data types + pure helpers (tested). Colours: blue/gold only (§18).
import type { Connection } from "./api";

export type FlowSource = "estimated" | "tick";
export interface FlowLevel { p: string; bid: string; ask: string }
export interface FlowBar {
  time_ms: number; o: string; h: string; l: string; c: string; v: string;
  delta: string; cvd: string; zone: "premium" | "discount" | "value" | "unknown"; source: FlowSource; levels: FlowLevel[];
}
export interface FlowProfile { rows: { p: string; v: string }[]; poc: string | null; vah: string | null; val: string | null; hvn: string[]; lvn: string[] }
// D101 AR Model layers as the indicator sent them (null = not sent)
export interface ArValues { env: string | null; location_zone: string | null; fib: string | null; value_side: string | null; path_zone: string | null; path_side: string | null; delta_source: string | null; confirm_time: number | null;
  // D108 Casper refinement fields (optional: older alerts omit them)
  close_pos?: string | null; cvd_slope?: string | null; open_vs_value?: string | null; prior_va_width_atr?: string | null }
export interface FlowSignal { time_ms: number; kind: string; label: string; direction: string; ar?: ArValues }
export interface ArLayer { key: "ENVIRONMENT" | "LOCATION" | "PATH" | "CONFIRMATION"; on: boolean; rule: string }
// D108 Casper 4h course refinements of the AR Model (each a plan-file switch)
export interface CasperRule { key: "PRICE_CONFIRMS" | "STACKED" | "CVD" | "CONDITION" | "BUNCHED" | "ROUND_STOP"; on: boolean; rule: string }
export interface ArRules { enabled: boolean; paper_only: boolean; verified: boolean; layers: ArLayer[]; casper?: CasperRule[] }
export interface FlowSkip { time_ms: number | null; direction: string | null; code: string; layer: string; label: string; detail: string | null; ar: ArValues }
export interface OrderFlowData {
  symbol: string; symbols: string[]; source: FlowSource; estimated: boolean; note: string; method: string;
  tick: string; row_size: string; sessions: string[]; session: string | null;
  bars: FlowBar[]; profile: FlowProfile | null; prior: (FlowProfile & { session: string }) | null;
  round_levels: string[]; signals: FlowSignal[]; ar?: ArRules; skips?: FlowSkip[]; ta_advisor?: TaAdvisor;
}

/** D109: TradingAgents advisor for Order Flow — advisory only (blocks only with the plan flag + a proven ledger). */
export interface TaAdvice { code: string; symbol: string; proxy: string; side: "LONG" | "SHORT" | "NEUTRAL" | null; raw: string | null; confidence: number | null; at: string }
export interface TaAdvisor { enabled: boolean; setting: string; blocks: boolean; at: string; advisory: boolean; session: string; advice: TaAdvice | null }

/** Public webhook base from the Connections list (same rule as the Connections page): permanent ngrok first. */
export function publicBaseOf(connections: Connection[]): string | undefined {
  const tunnel = connections.find((c) => c.id === "tunnel");
  const ti = connections.find((c) => c.id === "ngrok")?.tunnel;
  const permanent = ti?.mode === "ngrok" ? ti.public_url : undefined;
  return permanent ?? (tunnel?.status === "connected" ? tunnel.hints.public_url : undefined) ?? (ti?.mode === "cloudflare" ? ti.public_url : undefined);
}

/** One-line text of an alert's AR layers (env · location · path · delta source); "—" for a missing value. */
export function arSummary(a: ArValues | undefined): string {
  if (!a) return "no AR fields";
  const loc = a.location_zone ?? (a.fib != null ? `fib ${a.fib}` : "—");
  const path = a.path_zone ? `${a.path_zone}${a.path_side && a.path_side !== "INSIDE" ? ` ${a.path_side.toLowerCase()} Asia` : ""}` : "—";
  return `${a.env ?? "—"} · ${loc}${a.value_side ? ` ${a.value_side}` : ""} · ${path} · delta ${a.delta_source ?? "—"}`;
}

/** D108: "n of m Casper refinements ON" (empty list → "none configured"). */
export function casperSummary(c: CasperRule[] | undefined): string {
  if (!c || c.length === 0) return "none configured";
  return `${c.filter((x) => x.on).length} of ${c.length} ON`;
}

/** Snap each signal to the last bar that opened at/before it (markers must sit on a bar). */
export function snapSignals(bars: FlowBar[], signals: FlowSignal[]): (FlowSignal & { bar_ms: number })[] {
  const out: (FlowSignal & { bar_ms: number })[] = [];
  for (const s of signals) {
    let t: number | null = null;
    for (const b of bars) { if (b.time_ms <= s.time_ms) t = b.time_ms; else break; }
    if (t != null) out.push({ ...s, bar_ms: t });
  }
  return out;
}

/** Last `n` bars plus the price rows they cover (descending, numeric keys rounded to the row size). */
export function footprintWindow(bars: FlowBar[], n: number, row: number): { bars: FlowBar[]; rows: number[] } {
  const w = bars.slice(Math.max(0, bars.length - Math.max(1, n)));
  if (w.length === 0 || row <= 0) return { bars: w, rows: [] };
  let lo = Infinity, hi = -Infinity;
  for (const b of w) for (const l of b.levels) { const p = Number(l.p); lo = Math.min(lo, p); hi = Math.max(hi, p); }
  if (!Number.isFinite(lo)) return { bars: w, rows: [] };
  const rows: number[] = [];
  const steps = Math.round((hi - lo) / row);
  for (let i = steps; i >= 0; i--) rows.push(Number((lo + i * row).toFixed(6)));
  return { bars: w, rows };
}

export const priceKey = (p: string | number) => Number(Number(p).toFixed(6));

/** Volume shown in a cell: whole numbers stay whole, small estimated splits keep one decimal. */
export function fmtVol(v: string | number): string {
  const n = Number(v);
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return Number.isInteger(n) ? String(n) : n.toFixed(n >= 10 ? 0 : 1);
}

/** Signed delta / P&L-style text with ▲/▼ (never colour alone). */
export function signed(v: string | number): string {
  const n = Number(v);
  if (n === 0) return "0";
  return `${n > 0 ? "▲ +" : "▼ −"}${fmtVol(Math.abs(n))}`;
}

/** Bar width (0..100 %) for each profile row relative to the POC row. */
export function profileWidths(p: FlowProfile | null): { p: string; v: string; pct: number }[] {
  if (!p || p.rows.length === 0) return [];
  const max = Math.max(...p.rows.map((r) => Number(r.v)));
  return [...p.rows].reverse().map((r) => ({ ...r, pct: max > 0 ? Math.round((Number(r.v) / max) * 100) : 0 }));
}

export const SIGNAL_SHORT: Record<string, string> = {
  ABSORPTION: "ABS", DELTA_DIVERGENCE: "EXH", STACKED_IMBALANCE: "AGG", SWEEP: "SWP", POC_MAGNET: "POC",
};
