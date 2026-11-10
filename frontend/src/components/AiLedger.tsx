import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

interface Stats { n: number; hit_rate: number; brier: number; wilson_lb: number }
interface Preview { days: number; tool_runs: number; provider: string; est_usd: number; est_minutes: number; configured: boolean; with_vt: boolean; note: string }
interface Job { status: string; total: number; done: number; failed: number; skipped: number; current: string | null; provider: string; error: string | null }
export interface AiLedgerResp {
  session: string;
  symbol: string;
  schedule: string;
  live: { stats: Stats; state: string; badge: string; required_accuracy: number; min_calls: number; calls_needed: { at_current_rate: number | null; best_case: number | null } };
  backfill_estimate: { stats: Stats; label: string };
  coverage: { day: string; ta: boolean; vt: boolean; scored: boolean }[];
  job: Job;
  preview: Preview;
}
const pct = (x: number) => `${(x * 100).toFixed(0)}%`;
const card = "rounded-xl border border-border bg-card p-4";

export default function AiLedger() {
  const qc = useQueryClient();
  const [days, setDays] = useState(60);
  const q = useQuery({
    queryKey: ["ai-ledger"],
    queryFn: () => api<AiLedgerResp>("/api/ai-ledger"),
    refetchInterval: (query) => (query.state.data?.job.status === "running" ? 2000 : 15000),
  });
  const refresh = () => void qc.invalidateQueries({ queryKey: ["ai-ledger"] });
  const start = useMutation({ mutationFn: () => api("/api/ai-ledger/backfill", { method: "POST", body: JSON.stringify({ days }) }), onSettled: refresh });
  const cancel = useMutation({ mutationFn: () => api("/api/ai-ledger/backfill/cancel", { method: "POST" }), onSettled: refresh });
  const prev = useQuery({ queryKey: ["ai-ledger-preview", days], queryFn: () => api<Preview>(`/api/ai-ledger/backfill/preview?days=${days}`) });
  const d = q.data;
  if (!d) return <p role="status">Loading AI ledger…</p>;
  const { live, job } = d;
  const running = job.status === "running";
  const p = prev.data ?? d.preview;
  const gaps = d.coverage.filter((c) => !(c.ta && c.vt));
  const need = live.calls_needed;
  return (
    <section className={card} data-testid="ai-ledger-panel">
      <h2 className="font-semibold text-gold">AI bias record — {d.symbol} (TradingAgents + Vibe-Trading)</h2>
      <div className="mt-2 text-sm" data-testid="live-record">
        <b className="text-gold">Live record (this is the only thing that counts toward the proof):</b>
        <p className="text-blue">
          {live.stats.n} scored calls · accuracy {live.stats.n ? pct(live.stats.hit_rate) : "—"} · Wilson lower bound {live.stats.n ? pct(live.stats.wilson_lb) : "—"} · needs {live.min_calls}+ calls with lower bound ≥ {pct(live.required_accuracy)} · <b className="text-gold">{live.badge}</b>
        </p>
        <p className="text-blue" data-testid="calls-needed">
          Calls still needed: {live.state === "PROVEN" ? "proven" : need.at_current_rate != null ? `about ${need.at_current_rate} more at today's hit rate` : "not reachable at today's hit rate"}
          {live.state !== "PROVEN" && need.best_case != null && ` (at least ${need.best_case} even if every future call is right)`}.
        </p>
        <p className="text-xs text-blue">Daily job runs at {d.schedule} ET on weekdays; each day is scored automatically after 16:00 from the stored 09:30–16:00 bars.</p>
        {gaps.length > 0 ? (
          <p className="text-xs text-gold" data-testid="coverage-gaps">Days in the last 30 weekdays without a call from both tools: {gaps.map((g) => `${g.day.slice(5)}${g.ta ? " (no VT)" : ""}`).join(", ")}</p>
        ) : (
          <p className="text-xs text-blue">Every weekday of the last 30 has a call from both tools.</p>
        )}
      </div>
      <div className="mt-3 border-t border-border pt-3 text-sm" data-testid="backfill-box">
        <b className="text-gold">Fast-track backfill — estimate (possible hindsight), does NOT count toward the proof</b>
        <p className="text-blue" data-testid="bf-estimate">
          Backfill so far: {d.backfill_estimate.stats.n} scored calls{d.backfill_estimate.stats.n > 0 && ` · estimated accuracy ${pct(d.backfill_estimate.stats.hit_rate)}`}. The AI models may already know how those days ended, so treat this as an upper guess.
        </p>
        <label className="mt-2 block text-blue">
          Last <input aria-label="days" type="number" min={1} max={250} value={days} onChange={(e) => setDays(Math.max(1, Math.min(250, Number(e.target.value) || 1)))} className="mx-1 w-16 rounded border border-border bg-transparent px-1" /> trading days
        </label>
        <p className="text-xs text-blue" data-testid="bf-cost">
          Will run about {p.tool_runs} tool runs (TradingAgents{p.with_vt ? " + Vibe-Trading" : " only — Vibe-Trading not set up"}), provider {p.provider}, roughly ${p.est_usd.toFixed(2)} and {p.est_minutes} min. {p.note}. Needs stored 1-minute MNQ bars to score a day.
        </p>
        <div className="mt-2 flex gap-2">
          <button className="rounded-md border border-blue px-3 py-1 text-sm font-semibold text-blue disabled:opacity-50" disabled={running || start.isPending || !p.configured} onClick={() => start.mutate()}>
            Start backfill
          </button>
          {running && <button className="rounded-md border border-gold px-3 py-1 text-sm font-semibold text-gold" onClick={() => cancel.mutate()}>Cancel</button>}
        </div>
        {start.isError && <p role="alert" className="mt-1 text-gold">{(start.error as Error).message}</p>}
        {job.status !== "idle" && (
          <p className="mt-2 text-blue" data-testid="bf-progress">
            {job.status === "running" ? "Running" : job.status.replace(/_/g, " ")}: {job.done}/{job.total} done{job.skipped > 0 && ` (${job.skipped} already stored)`} · {job.failed} errors{job.current && ` · now ${job.current}`}
          </p>
        )}
        {job.error && <p role="alert" className="mt-1 text-gold" data-testid="bf-error">⚠ {job.error}</p>}
      </div>
    </section>
  );
}
