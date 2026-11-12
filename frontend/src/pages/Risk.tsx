import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { usePageTitle } from "../components/usePageTitle";
import RuleMeters from "../components/RuleMeters";
import FeedGuardSettings from "../components/FeedGuardSettings";
import type { MeterAcct } from "../lib/insights";
import { FastEvalPanel } from "../components/FastEvalPanel";
import { EvalModePanel, FirmAndSafety, ImpactTable, type PreviewResp, Versions, WhatIf } from "../components/RiskPanels";

interface Settings {
  version: number;
  settings: Record<string, unknown>;
  validation: { ok: boolean; errors: string[]; warnings: string[] };
  eval_mode_on: boolean;
  error: string | null;
}
interface Live {
  live: boolean; toggle_on: boolean; phrase: string;
  checklist: { check: string; ok: boolean; detail: string; skipped?: boolean }[];
  readiness?: { mode: "paper_sessions" | "off"; sessions: number; needed: number };
}

const btn = "rounded-md border px-3 py-1.5 text-sm font-semibold disabled:opacity-50";
function parsed(edit: Record<string, string>): Record<string, unknown> {
  const changes: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(edit)) { try { changes[k] = JSON.parse(v); } catch { changes[k] = v; } }
  return changes;
}
const show = (v: unknown) => (typeof v === "object" ? JSON.stringify(v) : String(v));

export default function Risk() {
  usePageTitle("Risk");
  const qc = useQueryClient();
  const [err, setErr] = useState("");
  const [livePhrase, setLivePhrase] = useState("");
  const [edit, setEdit] = useState<Record<string, string>>({});
  const st = useQuery({ queryKey: ["risk"], queryFn: () => api<Settings>("/api/risk/settings") });
  const [impact, setImpact] = useState<PreviewResp | null>(null);
  const lv = useQuery({ queryKey: ["live"], queryFn: () => api<Live>("/api/live"), refetchInterval: 30000 });
  const run = useMutation({
    mutationFn: (f: () => Promise<unknown>) => f(),
    onMutate: () => setErr(""),
    onSuccess: () => { ["risk", "evalmode", "live", "risk-versions"].forEach((k) => void qc.invalidateQueries({ queryKey: [k] })); setEdit({}); setImpact(null); },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Request failed"),
  });
  const plans = useQuery({ queryKey: ["plans"], queryFn: () => api<{ current: string; plans: { id: string; title: string }[] }>("/api/plans") });
  const dash = useQuery({ queryKey: ["dashboard"], queryFn: () => api<{ accounts: (MeterAcct & { id: number; label: string; error?: string })[] }>("/api/dashboard"), refetchInterval: 5000 });
  const low = useQuery({ queryKey: ["lowrisk"], queryFn: () => api<{ enabled: boolean; max_losses_per_day: number; max_trades_per_day: number }>("/api/risk/low-risk") });
  const s = st.data;
  if (!s) return <p role="status">Loading…</p>;
  const save = (changes: Record<string, unknown>) =>
    run.mutate(() => api("/api/risk/settings", { method: "PUT", body: JSON.stringify({ changes }) }));

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-gold">Risk management</h1>
      {err && <p role="alert" className="rounded-lg border border-gold p-3 text-sm text-goldLight">⚠ {err}</p>}
      {s.error && <p role="alert" className="text-goldLight">⚠ {s.error}</p>}

      <section className="rounded-xl border border-gold bg-card p-4">
        <h2 className="font-semibold text-gold">Lucid plan</h2>
        <p className="text-xs">All rules (target, drawdown, DLL, consistency, contract limits, payouts) follow this plan. Pick the one you bought.</p>
        <select aria-label="Lucid plan" className="mt-2" value={plans.data?.current ?? ""}
          onChange={(e) => run.mutate(() => api("/api/plans", { method: "PUT", body: JSON.stringify({ plan: e.target.value }) }).then(() => qc.invalidateQueries({ queryKey: ["plans"] })))}>
          {plans.data?.plans.map((p) => <option key={p.id} value={p.id}>{p.title.replace("Paytience rule profile — Lucid Trading ", "")}</option>)}
        </select>
      </section>

      <section className="rounded-xl border border-border bg-card p-4" data-testid="risk-gauges">
        <h2 className="font-semibold text-gold">Rule gauges</h2>
        <p className="text-xs">How close each account is to Lucid's limits right now. Gold = 50%+ used, red dot = 80%+.</p>
        {dash.isLoading && <p role="status" className="text-sm">Loading…</p>}
        {dash.error && <p role="alert" className="text-sm text-goldLight">⚠ Cannot load account limits.</p>}
        {dash.data && dash.data.accounts.length === 0 && <p className="mt-2 text-sm">No accounts yet.</p>}
        {dash.data?.accounts.map((a) => (
          <div key={a.id} className="mt-3 border-t border-border pt-2">
            <b className="text-sm text-gold">{a.label || a.id}</b> <span className="text-xs">{a.stage}</span>
            {a.error ? <p className="text-xs text-goldLight">⚠ {a.error}</p> : <RuleMeters a={a} />}
          </div>
        ))}
      </section>

      <section className="rounded-xl border border-gold bg-card p-4" data-testid="trading-mode">
        <h2 className="font-semibold text-gold">Trading mode · Intraday ✓</h2>
        <p className="text-xs">Main strategy (D55–D58): NOISE (noise-area momentum on Micro Nasdaq, fixed 1 micro) plus the afternoon fade, set with the buttons on the Strategy page. Entries only inside the morning window and never inside news blackouts; always flat before 4:40 PM ET. Gate toggles (order-block / SMT, AI threshold) are on the Strategy page and are OFF or advisory because testing on 2024–26 showed no gain. PAPER by default.</p>
      </section>

      <section className="rounded-xl border border-border bg-card p-4">
        <h2 className="font-semibold text-gold">Lower risk {low.data?.enabled ? "· ON" : "· OFF"}</h2>
        <p className="text-xs">Halves the risk on every trade and allows twice as many losing trades per day ({low.data?.max_losses_per_day ?? "—"} losses, {low.data?.max_trades_per_day ?? "—"} trades max now). Firm rules and stops unchanged.</p>
        <button data-testid="low-risk" className={`${btn} mt-2 ${low.data?.enabled ? "border-gold text-gold" : "border-blue text-blue"}`}
          onClick={() => run.mutate(() => api("/api/risk/low-risk", { method: "PUT", body: JSON.stringify({ enabled: !low.data?.enabled }) }).then(() => qc.invalidateQueries({ queryKey: ["lowrisk"] })))}>
          {low.data?.enabled ? "ON — turn off" : "OFF — turn on"}</button>
      </section>

      <section className="rounded-xl border border-border bg-card p-4" data-testid="trend-filters">
        <h2 className="font-semibold text-gold">Trend filters (TradingView indicators)</h2>
        <p className="text-xs">Only take a setup on the side of the trend. Computed from the same TradingView bars — no chart change. Off until backtests prove them.</p>
        <div className="mt-2 flex flex-wrap gap-4 text-sm">
          {([
            ["filters.trend.vwap", "Session VWAP"],
            ["filters.trend.ema200_5m", "EMA 200 (5 min)"],
            ["filters.trend.utbot_5m", "UT Bot (5 min)"],
            ["filters.trend.squeeze_5m_15m", "Squeeze Momentum rising (5 + 15 min)"],
          ] as const).map(([k, label]) => (
            <label key={k} className="flex items-center gap-2">
              <input type="checkbox" data-testid={k} checked={s.settings[k] === true} onChange={(e) => save({ [k]: e.target.checked })} />
              {label}
            </label>
          ))}
        </div>
      </section>

      <FeedGuardSettings key={String(s.version)} settings={s.settings} save={save} />

      <EvalModePanel />
      <FastEvalPanel />

      <section className="rounded-xl border border-gold bg-card p-4">
        <h2 className="font-semibold text-gold">Live trading {lv.data?.live ? "· LIVE" : "· PAPER"}</h2>
        <ul className="mt-2 grid gap-1 text-sm sm:grid-cols-2">
          {lv.data?.checklist.map((c) => (
            <li key={c.check} data-testid={`live-${c.check}`}>
              <span aria-hidden style={{ color: c.skipped ? "#D4AF37" : c.ok ? "#22C55E" : "#EF4444" }}>●</span> {c.check.replace(/_/g, " ")}
              {c.skipped && <span className="text-goldLight"> — SKIPPED (readiness check OFF)</span>}
              {!c.ok && <span className="opacity-75"> — {c.detail}</span>}
            </li>
          ))}
        </ul>
        {lv.data?.readiness && (
          <div className="mt-2 text-sm" data-testid="live-readiness">
            <label className="flex flex-wrap items-center gap-2">
              <span>Readiness check before live</span>
              <select aria-label="Live readiness check" value={lv.data.readiness.mode}
                onChange={(e) => run.mutate(() => api("/api/live/readiness", { method: "PUT", body: JSON.stringify({ mode: e.target.value }) }))}>
                <option value="paper_sessions">{lv.data.readiness.needed} clean paper sessions (default)</option>
                <option value="off">Off — skip this one item</option>
              </select>
            </label>
            <p className="text-xs opacity-75">
              {lv.data.readiness.mode === "off"
                ? "OFF: only the paper-sessions item is skipped (audit-logged). Every other live gate still applies."
                : `Progress ${Math.min(lv.data.readiness.sessions, lv.data.readiness.needed)}/${lv.data.readiness.needed}: completed sessions in which an active strategy traded on paper with no error banner (order rejections raise one).`}
            </p>
          </div>
        )}
        {lv.data?.toggle_on ? (
          <button className={`${btn} mt-2 border-blue text-blue`} onClick={() => run.mutate(() => api("/api/live", { method: "PUT", body: JSON.stringify({ enabled: false }) }))}>Turn live toggle off</button>
        ) : (
          <div className="mt-2 flex flex-wrap gap-2">
            <input aria-label="Live phrase" placeholder={lv.data?.phrase} value={livePhrase} onChange={(e) => setLivePhrase(e.target.value)} />
            <button disabled={livePhrase !== lv.data?.phrase} className={`${btn} border-gold text-gold`}
              onClick={() => run.mutate(() => api("/api/live", { method: "PUT", body: JSON.stringify({ enabled: true, confirm: livePhrase }) }))}>Enable live toggle</button>
          </div>
        )}
      </section>

      <section className="rounded-xl border border-border bg-card p-4">
        <h2 className="font-semibold text-gold">My settings · v{s.version}</h2>
        {!s.validation.ok && <p className="text-sm text-goldLight">{s.validation.errors.join(" · ")}</p>}
        <details className="mt-2"><summary className="cursor-pointer text-sm text-blue">Show all {Object.keys(s.settings).length} settings</summary>
        <table className="mt-2 w-full text-sm"><tbody>
          {Object.entries(s.settings).map(([k, v], i, arr) => (
            <tr key={k} className={`border-t border-border ${i === 0 || arr[i - 1]?.[0].split(".")[0] !== k.split(".")[0] ? "settings-group" : ""}`}>
              <td className="py-1 pr-2" title={k}><span className="text-[10px] uppercase tracking-wider opacity-60">{(k.split(".")[0] ?? "").replace(/_/g, " ")}</span> {k.split(".").slice(1).join(".").replace(/_/g, " ")}</td>
              <td><input aria-label={k} className="w-full" value={edit[k] ?? show(v)} onChange={(e) => { setEdit({ ...edit, [k]: e.target.value }); setImpact(null); }} /></td>
            </tr>
          ))}
        </tbody></table></details>
        <div className="mt-3 flex flex-wrap gap-2">
          <button disabled={!Object.keys(edit).length} data-testid="risk-preview" className={`${btn} border-blue text-blue`}
            onClick={() => { setErr(""); api<PreviewResp>("/api/risk/preview", { method: "POST", body: JSON.stringify({ changes: parsed(edit) }) }).then(setImpact, (e) => setErr(e instanceof ApiError ? e.message : "Preview failed")); }}>Preview impact</button>
          <button disabled={!impact?.valid} data-testid="risk-save" className={`${btn} border-gold text-gold`} onClick={() => save(parsed(edit))}>Save (validated)</button>
          {Object.keys(edit).length > 0 && <button className={`${btn} border-border text-blue`} onClick={() => { setEdit({}); setImpact(null); }}>Discard</button>}
        </div>
        {impact && !impact.valid && <p role="alert" className="mt-2 text-sm text-goldLight">⚠ {impact.errors.map((e) => (typeof e === "string" ? e : JSON.stringify(e))).join(" · ")}</p>}
        {impact?.preview && <><p className="mt-2 text-sm font-semibold text-gold">Impact Preview (not saved yet)</p><ImpactTable p={impact.preview} testid="risk-impact" /></>}
        {impact?.warnings.map((w) => <p key={w} className="text-xs text-goldLight">{w}</p>)}
      </section>
      <Versions />
      <WhatIf settings={s.settings} />
      <FirmAndSafety />
    </div>
  );
}
