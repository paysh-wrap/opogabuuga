import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

// D122: dynamic trailing stop + cushion level controls — per-strategy toggles and the level editor. Every save is a new
// versioned My Settings entry, validated by the server (rollback on the Risk page). UNVERIFIED: no backtest.
interface SettingsResp { version: number; settings: Record<string, unknown> }

export const TRAIL_STRATEGIES: [string, string][] = [
  ["noise", "NOISE"], ["pm_fade", "Afternoon fade"], ["ai_bias", "AI only"], ["ai_duo", "AI Duo"], ["order_flow", "Order Flow"],
];
const card = "rounded-xl border border-border bg-card p-4";
const field = "w-20 rounded border border-border bg-transparent px-1 text-gold";
const btn = (on: boolean) => `rounded-md border px-2 py-0.5 text-xs font-semibold ${on ? "border-gold text-gold" : "border-blue text-blue"}`;

// [setting key, label, min, max, whole number?]
const LEVELS: [string, string, number, number, boolean][] = [
  ["strategy.dynamic_trail.activate_r", "Trail starts at +R", 0.5, 3, false],
  ["strategy.dynamic_trail.min_distance_ticks", "Min distance (ticks)", 2, 200, true],
  ["strategy.cushion.normal_min", "Normal ≥ (share of MLL distance)", 0.1, 0.95, false],
  ["strategy.cushion.reduce_min", "Reduce ≥", 0.1, 0.95, false],
  ["strategy.cushion.minimal_min", "Minimal ≥ (below = STOP)", 0.05, 0.9, false],
  ["strategy.cushion.reduce_size_minus", "Reduce: micros off (min 1 stays)", 1, 10, true],
  ["strategy.cushion.minimal_max_trades", "Minimal: max trades / day", 1, 5, true],
];

export function levelErrors(v: Record<string, string>): string[] {
  const out: string[] = [];
  for (const [k, label, lo, hi, int] of LEVELS) {
    const n = Number(v[k]);
    if (v[k] === "" || v[k] == null || !Number.isFinite(n) || n < lo || n > hi || (int && !Number.isInteger(n))) out.push(`${label}: ${lo}–${hi}${int ? " (whole number)" : ""}`);
  }
  const nm = Number(v["strategy.cushion.normal_min"]);
  const rd = Number(v["strategy.cushion.reduce_min"]);
  const mn = Number(v["strategy.cushion.minimal_min"]);
  if (!(mn < rd && rd < nm)) out.push("Levels must be Minimal < Reduce < Normal");
  return out;
}

export default function TrailCushionCard() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["risk-settings"], queryFn: () => api<SettingsResp>("/api/risk/settings") });
  const [draft, setDraft] = useState<Record<string, string> | null>(null);
  const save = useMutation({
    mutationFn: (changes: Record<string, unknown>) =>
      api("/api/risk/settings", { method: "PUT", body: JSON.stringify({ changes, note: "Strategy page: dynamic trail / cushion (D122)" }) }),
    onSettled: () => void qc.invalidateQueries({ queryKey: ["risk-settings"] }),
  });
  const s = q.data?.settings;
  if (!s) return <p role="status">Loading trailing stop / cushion…</p>;
  const vals = draft ?? Object.fromEntries(LEVELS.map(([k]) => [k, String(s[k] ?? "")]));
  const errs = levelErrors(vals);
  const steps = (s["strategy.dynamic_trail.steps"] as { until_r: string | null; k: string }[] | undefined) ?? [];
  return (
    <section className={card} data-testid="trail-cushion">
      <h2 className="font-semibold text-gold">
        Dynamic trailing stop &amp; cushion levels{" "}
        <span className="ml-1 rounded border border-gold px-1 text-[11px] text-gold" data-testid="trail-unverified">UNVERIFIED · no backtest</span>
      </h2>
      <p className="text-xs text-blue" data-testid="trail-rule">
        Both only ever tighten. Trail: from +{String(s["strategy.dynamic_trail.activate_r"])}R the stop goes to breakeven + fees, then follows k × ATR or the last
        5-minute swing (the wider one), k {steps.map((x) => `${x.k}${x.until_r ? ` until ${x.until_r}R` : " after"}`).join(", ")}, tighter when volatility is low.
        The take-profit stays. Cushion = equity − MLL as a share of the MLL distance: Reduce takes micros off, Minimal trades 1 micro once a day, below Minimal
        no new entries until the next session. Size tables, kill switch, DLL and consistency rules are unchanged.
      </p>
      <table className="mt-2 text-sm">
        <thead><tr><th className="pr-4 text-left text-gold">Strategy</th><th className="pr-4 text-gold">Dynamic trail</th><th className="text-gold">Cushion levels</th></tr></thead>
        <tbody>
          {TRAIL_STRATEGIES.map(([k, name]) => {
            const tr = s[`strategy.dynamic_trail.${k}`] === true;
            const cu = s[`strategy.cushion.${k}`] === true;
            return (
              <tr key={k}>
                <td className="pr-4 text-blue">{name}</td>
                <td className="pr-4 text-center">
                  <button aria-pressed={tr} aria-label={`Dynamic trail ${name}`} data-testid={`trail-${k}`} className={btn(tr)} onClick={() => save.mutate({ [`strategy.dynamic_trail.${k}`]: !tr })}>{tr ? "ON" : "OFF"}</button>
                </td>
                <td className="text-center">
                  <button aria-pressed={cu} aria-label={`Cushion levels ${name}`} data-testid={`cushion-${k}`} className={btn(cu)} onClick={() => save.mutate({ [`strategy.cushion.${k}`]: !cu })}>{cu ? "ON" : "OFF"}</button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="mt-3 flex flex-wrap gap-3 text-sm">
        {LEVELS.map(([k, label]) => (
          <label key={k} className="text-blue">
            {label} <input aria-label={label} className={field} value={vals[k] ?? ""} onChange={(e) => setDraft({ ...vals, [k]: e.target.value })} />
          </label>
        ))}
        <button
          data-testid="trail-cushion-save"
          disabled={errs.length > 0 || !draft || save.isPending}
          className="rounded-md border border-gold px-3 py-1 text-sm font-semibold text-gold disabled:opacity-50"
          onClick={() => {
            save.mutate(Object.fromEntries(LEVELS.map(([k, , , , int]) => [k, int ? Number(vals[k]) : vals[k]])));
            setDraft(null);
          }}
        >
          Save levels
        </button>
      </div>
      {errs.length > 0 && <p role="alert" className="mt-1 text-xs text-goldLight">⚠ {errs.join(" · ")}</p>}
      {save.isError && <p role="alert" className="mt-1 text-xs text-goldLight">⚠ Not saved — the server refused these values.</p>}
    </section>
  );
}

export interface CushionView {
  usd: string; pct: string; level: "NORMAL" | "REDUCE" | "MINIMAL" | "STOP"; strategies: string[]; trail_strategies: string[]; unverified: boolean;
}

/** D122 state chip: the account's current cushion level (Dashboard / Accounts). */
export function CushionChip({ c }: { c?: CushionView | null }) {
  if (!c) return null;
  const warn = c.level !== "NORMAL";
  const off = c.strategies.length === 0;
  return (
    <span
      data-testid="cushion-chip"
      title={`Cushion $${c.usd} = ${c.pct}% of the MLL distance · applies to: ${off ? "no strategy (toggles OFF)" : c.strategies.join(", ")} · UNVERIFIED`}
      className={`rounded border px-1.5 text-[11px] font-semibold ${warn ? "border-gold text-goldLight" : "border-border text-blueLight"}`}
    >
      CUSHION {c.level} · {c.pct}%{off ? " (off)" : ""}
    </span>
  );
}
