import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { badge } from "../lib/theme";
import type { PresetRow, StrategiesResp } from "./StrategyButtons";

// D82: NOISE strategy presets (config/strategy_presets.yaml via /api/strategies.presets). A preset only sets NOISE
// parameters, the fade button and the size table — never a safety rule. Applying saves a versioned, audited My Settings
// entry (strategy.preset); the next NEW trade uses it. PAPER stays the default mode; nothing here goes live.
const k$ = (v: string) => `${Math.round(Number(v) / 1000)}K`;
const card = "rounded-xl border border-border bg-card p-4";

function sizeText(p: PresetRow): string {
  return p.size
    .map((t) => `${t.contracts} micro${t.contracts > 1 ? "s" : ""}${t.brake_below ? `, ${t.brake_contracts} while the cushion is under ${Math.round(Number(t.brake_below) * 100)}% of the loss limit` : ""}`)
    .join("; ");
}

export default function StrategyPresets() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["strategies"], queryFn: () => api<StrategiesResp>("/api/strategies"), refetchInterval: 30000 });
  const [pick, setPick] = useState<string | null>(null);
  const apply = useMutation({
    mutationFn: (p: PresetRow | null) =>
      api("/api/risk/settings", { method: "PUT", body: JSON.stringify({ changes: { "strategy.preset": p ? p.key : null }, note: p ? `Strategy preset: ${p.label}` : "Strategy preset: custom (plan file values)" }) }),
    onSettled: () => void qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
  const d = q.data?.presets;
  if (!d) return null;
  const chosen = d.rows.find((r) => r.key === (pick ?? d.active ?? d.rows.find((x) => x.recommended)?.key));
  return (
    <section className={card} data-testid="strategy-presets">
      <h2 className="font-semibold text-gold">Strategy preset — NOISE on MNQ</h2>
      <p className="text-xs text-blue">
        A preset sets only the NOISE settings, the afternoon-fade button and the size table. Every preset keeps a stop loss on every trade, the hourly band/VWAP exits and the 16:00 flat, and none changes the kill switch, loss limits or any risk check. It applies to the next NEW trade; the mode stays PAPER until you change it.
      </p>
      <p className="mt-1 text-sm" data-testid="preset-active">
        Active: <b className="text-gold">{d.active ? d.rows.find((r) => r.key === d.active)?.label ?? d.active : "Custom (the values in the plan file)"}</b>
        {d.active && (
          <button type="button" className="ml-3 rounded-md border border-blue px-2 py-0.5 text-xs font-semibold text-blue disabled:opacity-50" disabled={apply.isPending} onClick={() => apply.mutate(null)}>
            Back to custom
          </button>
        )}
      </p>
      <div className="mt-3 grid gap-3 lg:grid-cols-3" role="radiogroup" aria-label="Strategy preset">
        {d.rows.map((p) => {
          const on = chosen?.key === p.key;
          return (
            <button
              key={p.key}
              type="button"
              role="radio"
              aria-checked={on}
              data-testid={`preset-${p.key}`}
              onClick={() => setPick(p.key)}
              className={`rounded-lg border p-3 text-left ${on ? "border-gold" : "border-border"}`}
            >
              <span className="block font-semibold text-gold">{p.label}{p.recommended && <span className="ml-2 rounded border border-gold px-1 text-xs">recommended</span>}{p.superseded && <span className="ml-2 rounded border border-blue px-1 text-xs text-blue" data-testid={`preset-superseded-${p.key}`}>superseded</span>}{d.active === p.key && <span className="ml-2 rounded border border-blue px-1 text-xs text-blue">active</span>}</span>
              <span className="mt-1 block text-sm text-blue">{p.summary}</span>
              <span className="mt-2 block text-sm" data-testid={`preset-rates-${p.key}`}>
                Eval odds: <b className="text-gold">{p.odds_text}</b>
                <span className="text-blue"> · {p.study}{p.held_out ? ", held-out 2024–26" : ""}</span>
              </span>
              {p.warning && (
                <span className="mt-1 block text-xs text-gold" data-testid={`preset-warning-${p.key}`}>
                  <span aria-hidden style={{ color: badge.bad }}>▲</span> {p.warning}
                </span>
              )}
            </button>
          );
        })}
      </div>
      {chosen && (
        <div className="mt-3 text-sm" data-testid="preset-detail">
          <p><b className="text-gold">{chosen.label}</b> sets: NOISE ${Math.round(Number(chosen.stop_usd))} stop per micro · afternoon fade <b className="text-gold">{chosen.fade ? "ON" : "OFF"}</b> · {chosen.profit_lock ? <>profit lock: at +{chosen.profit_lock.trigger_pts} pt the stop moves to entry +{chosen.profit_lock.lock_pts} pt, and a locked-stop exit ends NOISE for the day</> : "no profit lock"} · size: <b className="text-gold">{sizeText(chosen)}</b></p>
          {!chosen.matches_plan && (
            <p className="mt-1 text-xs text-gold" data-testid="preset-mismatch"><span aria-hidden style={{ color: badge.bad }}>▲</span> Built for a {chosen.account} account; the loaded plan is {k$(d.plan_account_size)} — the size above still applies to every account, so check it fits.</p>
          )}
          <button
            type="button"
            className="mt-2 rounded-md border border-gold px-3 py-1 font-semibold text-gold disabled:opacity-50"
            disabled={apply.isPending || d.active === chosen.key}
            onClick={() => apply.mutate(chosen)}
          >
            {d.active === chosen.key ? "Applied" : `Apply ${chosen.label}`}
          </button>
        </div>
      )}
    </section>
  );
}
