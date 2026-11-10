import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { etTime } from "../lib/time";
import { signedUsd } from "../lib/insights";

const card = "rounded-xl border border-border bg-card p-4";
const usd = (v?: string | null) => (v == null ? "—" : `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })}`);

// ---------- $50k / $70k progress + next Friday payout estimate (§14, §18 Dashboard) ----------
interface PlanResp {
  tracker: { year: number; ytd_net: string; target_net: string; floor_net: string; target_pct: string; floor_pct: string };
  next_payout: { check_at: string | null; frequency: string; total: string; accounts: { account_id: number; label: string; kind?: string | null; amount?: string; reason?: string; error?: string }[] };
}

function Bar({ label, pct, testid }: { label: string; pct: number; testid: string }) {
  const w = Math.max(0, Math.min(100, pct));
  return (
    <div data-testid={testid}>
      <div className="flex justify-between text-xs"><span>{label}</span><span className="text-goldLight">{pct.toFixed(1)}%</span></div>
      <div className="mt-1 h-2 rounded bg-border" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(w)}>
        <div className="h-2 rounded bg-gold" style={{ width: `${w}%` }} />
      </div>
    </div>
  );
}

export function PlanProgress() {
  const q = useQuery({ queryKey: ["plan-tracker"], queryFn: () => api<PlanResp>("/api/plan"), refetchInterval: 60_000 });
  if (q.isLoading) return <section className={card}><p role="status">Loading plan…</p></section>;
  if (q.error || !q.data?.tracker) return <section className={card}><p role="alert" className="text-goldLight">⚠ Cannot load the payout plan.</p></section>;
  const { tracker: t, next_payout: n } = q.data;
  return (
    <section className={card} data-testid="dash-plan">
      <h2 className="font-semibold text-gold">{t.year} income plan · net {usd(t.ytd_net)}</h2>
      <div className="mt-2 space-y-2">
        <Bar testid="progress-floor" label={`Floor goal ${usd(t.floor_net)}`} pct={Number(t.floor_pct)} />
        <Bar testid="progress-target" label={`Target ${usd(t.target_net)}`} pct={Number(t.target_pct)} />
      </div>
      <div className="mt-3 text-sm" data-testid="next-payout">
        <b className="text-gold">Next payout estimate {usd(n.total)}</b>
        {n.check_at ? <> · check {new Date(n.check_at).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })} {etTime(n.check_at)}</> : <> · {n.frequency}</>}
        {n.accounts.length === 0 && <p className="text-xs">No FUNDED accounts yet.</p>}
        {n.accounts.map((a) => (
          <p key={a.account_id} className="text-xs">{a.label}: {a.error ? `⚠ ${a.error}` : a.kind ? `${a.kind} ${usd(a.amount)}` : `none (${a.reason?.replace(/_/g, " ").toLowerCase()})`}</p>
        ))}
      </div>
    </section>
  );
}

// ---------- Eval pace incl. 40% consistency headroom (§11C, §18) ----------
export interface EvalPace {
  id: number; label: string; profit: string; target: string; target_left: string; profitable_days: number; min_profitable_days: number;
  sessions_used: number; target_sessions: number; max_sessions: number; largest_day: string;
  consistency_cap: string | null; consistency_day_stop: string | null; consistency_headroom: string | null; consistency_pct: string | null;
}

export function useEvalPace(id: number, enabled = true) {
  return useQuery({ queryKey: ["eval-pace", id], queryFn: () => api<EvalPace>(`/api/accounts/${id}/eval-pace`), enabled, refetchInterval: 30_000 });
}

export function EvalPaceCard({ id }: { id: number }) {
  const q = useEvalPace(id);
  if (q.isLoading) return <p role="status" className="text-xs">Loading eval pace…</p>;
  if (q.error || !q.data) return <p role="alert" className="text-xs text-goldLight">⚠ Eval pace unavailable{q.error instanceof ApiError ? `: ${q.error.message}` : ""}</p>;
  const p = q.data;
  return (
    <div className="mt-3 rounded-lg border border-border p-2 text-xs" data-testid={`pace-${id}`}>
      <b className="text-gold">Eval pace</b> · profit {signedUsd(Number(p.profit))} of {usd(p.target)} (left {usd(p.target_left)})
      · profitable days <b className="text-gold">{p.profitable_days}/{p.min_profitable_days}</b> · sessions {p.sessions_used} (target {p.target_sessions}, max {p.max_sessions})
      {p.consistency_cap && (
        <span data-testid={`headroom-${id}`}> · {p.consistency_pct}% consistency: largest day {usd(p.largest_day)} of cap {usd(p.consistency_cap)} → headroom <b className="text-gold">{usd(p.consistency_headroom)}</b> (day stop {usd(p.consistency_day_stop)})</span>
      )}
    </div>
  );
}

// ---------- Model-fail cooldown banner + typed clear (§6, §19) ----------
interface Cd { symbol: string; profile: string; streak: number; until_session: string | null; active: boolean }
export const CLEAR_PHRASE = "CLEAR COOLDOWN"; // must match backend CLEAR_PHRASE

export function CooldownBanner() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["cooldowns"], queryFn: () => api<{ cooldowns: Cd[] }>("/api/cooldowns"), refetchInterval: 30_000 });
  const [open, setOpen] = useState<string | null>(null);
  const [typed, setTyped] = useState("");
  const [err, setErr] = useState("");
  const clear = useMutation({
    mutationFn: (c: Cd) => api(`/api/cooldowns/${encodeURIComponent(c.profile)}/clear`, { method: "POST", body: JSON.stringify({ confirm: typed, symbol: c.symbol }) }),
    onSuccess: () => { setOpen(null); setTyped(""); setErr(""); void qc.invalidateQueries({ queryKey: ["cooldowns"] }); },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Clear failed"),
  });
  if (q.error) return <p role="alert" className="text-sm text-goldLight">⚠ Cannot load cooldowns.</p>;
  const active = q.data?.cooldowns.filter((c) => c.active) ?? [];
  if (active.length === 0) return null;
  return (
    <div className="space-y-2">
      {active.map((c) => {
        const k = `${c.symbol}-${c.profile}`;
        return (
          <div key={k} role="alert" data-testid={`cooldown-${k}`} className="rounded-lg border border-gold bg-card p-3 text-sm text-goldLight">
            ⚠ Cooldown: <b className="text-gold">{c.symbol} {c.profile}</b> paused after {c.streak} model failures{c.until_session ? ` until session ${c.until_session}` : ""}.
            <button className="ml-2 rounded border border-blue px-2 py-0.5 text-xs text-blue" onClick={() => { setOpen(open === k ? null : k); setTyped(""); setErr(""); }}>Clear…</button>
            {open === k && (
              <form className="mt-2 flex flex-wrap items-center gap-2 text-xs" onSubmit={(e) => { e.preventDefault(); clear.mutate(c); }}>
                <span>Type <b className="text-gold">{CLEAR_PHRASE}</b>:</span>
                <input aria-label="Cooldown clear confirmation" value={typed} onChange={(e) => setTyped(e.target.value)} />
                <button type="submit" disabled={typed !== CLEAR_PHRASE || clear.isPending} className="rounded border border-gold px-2 py-0.5 font-semibold text-gold disabled:opacity-40">Clear cooldown</button>
                {err && <span role="alert">⚠ {err}</span>}
              </form>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ---------- approval queue, blackouts, raw bias (§18 Dashboard) ----------
export function ApprovalQueue() {
  const q = useQuery({ queryKey: ["automation"], queryFn: () => api<{ mode: string; approvals: { signal_id: number; expires: string }[] }>("/api/automation"), refetchInterval: 10_000 });
  const list = q.data?.approvals ?? [];
  return (
    <section className={card} data-testid="dash-approvals">
      <h2 className="font-semibold text-gold">Approval queue</h2>
      {q.isLoading && <p role="status" className="text-sm">Loading…</p>}
      {q.data && list.length === 0 && <p className="text-sm">Nothing waiting{q.data.mode.startsWith("SEMI") ? "" : ` (approvals appear in SEMI-AUTO; now ${q.data.mode})`}.</p>}
      {list.map((a) => <p key={a.signal_id} className="text-sm">Signal #{a.signal_id} · expires {etTime(a.expires)} ET · <Link to="/trade">Review on Trade</Link></p>)}
    </section>
  );
}

export function BiasAndBlackouts() {
  const bias = useQuery({ queryKey: ["bias"], queryFn: () => api<{ decisions: { proxy: string; raw: string; mapped: string }[] }>("/api/bias"), refetchInterval: 60_000 });
  const plan = useQuery({ queryKey: ["plan"], queryFn: () => api<{ calendar_loaded: boolean; news: { at: string; title: string; no_entry_from: string; no_entry_until: string }[] }>("/api/today/plan"), refetchInterval: 60_000 });
  return (
    <section className={card} data-testid="dash-bias">
      <h2 className="font-semibold text-gold">Bias &amp; blackouts</h2>
      {bias.data?.decisions.length === 0 && <p className="text-sm">Bias not run yet — no bias, no trading.</p>}
      {bias.data?.decisions.map((b) => <p key={b.proxy} className="text-sm">{b.proxy}: <b className="text-gold">{b.raw}</b> → {b.mapped}</p>)}
      {plan.data && !plan.data.calendar_loaded && <p className="text-sm text-goldLight">⚠ Calendar not loaded — no trading until it is.</p>}
      {plan.data?.calendar_loaded && plan.data.news.length === 0 && <p className="text-sm">No high-impact news today.</p>}
      {plan.data?.news.map((n) => <p key={n.at + n.title} className="text-sm">{etTime(n.at)} {n.title} · blackout {etTime(n.no_entry_from)}–{etTime(n.no_entry_until)}</p>)}
    </section>
  );
}
