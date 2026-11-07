import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { usePageTitle } from "../components/usePageTitle";
import { etTime } from "../lib/time";
import WhyNoTrade from "../components/WhyNoTrade";
import { EvalPaceCard } from "../components/DashboardExtras";
import { ApiError } from "../lib/api";

interface Sig { id: number; symbol: string; profile: string; direction: string; status: string; skip_reason: string | null; score: string | null; at: string }
interface Tr { id: number; account_id: number; symbol: string; direction: string; qty: number; entry: string; exit: string | null; pnl: string | null; net_r: string | null; exit_reason: string | null; opened_at: string }

interface Plan {
  session: string; calendar_loaded: boolean;
  news: { at: string; title: string; no_entry_from: string; no_entry_until: string; flatten_at: string }[];
  news_rules: { no_entry_before_min: number; flatten_before_min: number };
  windows: { symbol: string; label: string; windows: [string, string][] }[];
  accounts: { id: number; label: string; stage: string; armed: boolean; selected: boolean }[];
  attested_today: boolean;
  preflight: { ok: boolean; failures: string[]; at: string } | null;
  cooldowns: { symbol: string; profile: string; until_session: string | null }[];
  eval_pace: { id: number; label: string; profit: string; target: string; profitable_days: number; min_profitable_days: number;
    sessions_used: number; target_sessions: number; max_sessions: number }[];
}

function ReadyToTrade({ plan }: { plan: Plan }) {
  const qc = useQueryClient();
  const [confirm, setConfirm] = useState(false);
  const [msg, setMsg] = useState("");
  const run = useMutation({
    mutationFn: async () => {
      if (!plan.attested_today) await api("/api/attestation", { method: "POST", body: JSON.stringify({ confirm: true }) });
      return api<{ ok: boolean; failures: string[] }>("/api/automation/preflight", { method: "POST" });
    },
    onSuccess: (r) => setMsg(r.ok ? "Pre-flight passed. Arm accounts on the Automation page." : `Pre-flight failed: ${r.failures.join(", ")}`),
    onError: (e) => setMsg(e instanceof ApiError ? e.message : "Request failed"),
    onSettled: () => void qc.invalidateQueries({ queryKey: ["plan"] }),
  });
  return (
    <div className="space-y-2">
      {!plan.attested_today && (
        <label className="flex items-start gap-2 text-sm">
          <input type="checkbox" checked={confirm} onChange={(e) => setConfirm(e.target.checked)} />
          <span>I hold no open positions at other firms or platforms that could hedge or correlate with these accounts.</span>
        </label>
      )}
      <button className="rounded-md border border-gold px-4 py-2 font-semibold text-gold disabled:opacity-50"
        disabled={run.isPending || (!plan.attested_today && !confirm)} onClick={() => run.mutate()}>
        {run.isPending ? "Checking…" : "Ready to trade"}
      </button>
      {msg && <p role="status" className="text-sm text-goldLight">{msg}</p>}
    </div>
  );
}

function PlanPanel({ plan }: { plan: Plan }) {
  const pf = plan.preflight;
  return (
    <>
      <section className="rounded-xl border border-border bg-card p-4" data-testid="ready">
        <h2 className="font-semibold text-gold">Ready to trade</h2>
        <p className="text-sm">Attestation: <b className="text-gold">{plan.attested_today ? "done today" : "needed"}</b> · Last pre-flight:{" "}
          <b className="text-gold">{pf ? `${pf.ok ? "passed" : `failed (${pf.failures.join(", ")})`} at ${etTime(pf.at)}` : "not run yet"}</b></p>
        <p className="text-sm">Armed / selected: {plan.accounts.length === 0 ? "none" : plan.accounts.map((a) => `${a.label} (${a.stage}${a.armed ? ", armed" : ""})`).join(" · ")}</p>
        <p className="text-sm">Cooldowns: {plan.cooldowns.length === 0 ? "none active" : plan.cooldowns.map((c) => `${c.symbol} ${c.profile}${c.until_session ? ` until ${c.until_session}` : ""}`).join(" · ")}</p>
        <div className="mt-2"><ReadyToTrade plan={plan} /></div>
      </section>

      <section className="rounded-xl border border-border bg-card p-4" data-testid="blackouts">
        <h2 className="font-semibold text-gold">High-impact news and blackouts</h2>
        <p className="text-xs text-blueLight">No entries {plan.news_rules.no_entry_before_min} min before; flat {plan.news_rules.flatten_before_min} min before.</p>
        {!plan.calendar_loaded && <p className="text-sm text-goldLight">⚠ Calendar not loaded — no trading until it is.</p>}
        {plan.calendar_loaded && plan.news.length === 0 && <p className="text-sm">None today.</p>}
        {plan.news.map((n) => (
          <p key={n.at + n.title} className="text-sm">{etTime(n.at)} · {n.title} — no entry {etTime(n.no_entry_from)} to {etTime(n.no_entry_until)} · flat by {etTime(n.flatten_at)}</p>
        ))}
      </section>

      <section className="rounded-xl border border-border bg-card p-4" data-testid="windows">
        <h2 className="font-semibold text-gold">Entry windows (ET)</h2>
        {plan.windows.map((w) => (
          <p key={w.symbol + w.label} className="text-sm"><b>{w.symbol}</b> · {w.label}: {w.windows.map(([a, b]) => `${a}–${b}`).join(", ")}</p>
        ))}
      </section>

      {plan.eval_pace.length > 0 && (
        <section className="rounded-xl border border-border bg-card p-4" data-testid="pace">
          <h2 className="font-semibold text-gold">Evaluation pace</h2>
          {plan.eval_pace.map((p) => <div key={p.id}><b className="text-sm">{p.label}</b><EvalPaceCard id={p.id} /></div>)}
        </section>
      )}
    </>
  );
}

export default function Today() {
  usePageTitle("Today");
  const q = useQuery({ queryKey: ["today"], queryFn: () => api<{ signals: Sig[]; trades: Tr[] }>("/api/today"), refetchInterval: 10000 });
  const qc = useQueryClient();
  const bias = useQuery({ queryKey: ["bias"], queryFn: () => api<{ decisions: { proxy: string; raw: string; mapped: string; reasoning: string; blend?: string | null }[] }>("/api/bias"), refetchInterval: 60000 });
  const runBias = useMutation({ mutationFn: () => api("/api/bias/run", { method: "POST" }), onSettled: () => void qc.invalidateQueries({ queryKey: ["bias"] }) });
  const plan = useQuery({ queryKey: ["plan"], queryFn: () => api<Plan>("/api/today/plan"), refetchInterval: 15000 });
  const d = q.data;
  if (!d) return <p role="status">Loading…</p>;
  const net = d.trades.reduce((s, t) => s + Number(t.pnl ?? 0), 0);
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-gold">Today</h1>
      <p className="text-sm">{d.signals.length} signals · {d.signals.filter((s) => s.status === "PASS").length} passed · {d.trades.length} trades · net{" "}
        <b className="text-gold">{net > 0 ? "▲ +" : net < 0 ? "▼ −" : ""}${Math.abs(net).toFixed(2)}</b></p>

      {plan.data && <PlanPanel plan={plan.data} />}
      <WhyNoTrade />

      <section className="rounded-xl border border-border bg-card p-4">
        <div className="flex items-center justify-between gap-2">
          <h2 className="font-semibold text-gold">Bias today (TradingAgents + Vibe-Trading + OpenBB)</h2>
          <button className="rounded-md border border-blue px-3 py-1 text-sm font-semibold text-blue disabled:opacity-50" disabled={runBias.isPending}
            onClick={() => runBias.mutate()}>{runBias.isPending ? "Running… (up to 10 min)" : "Run now"}</button>
        </div>
        {bias.data?.decisions.length === 0 && <p className="text-sm">Not run yet (02:40 ET). No bias = no trading.</p>}
        {bias.data?.decisions.map((b, i) => (
          <details key={i} className="text-sm" data-testid={`bias-${b.proxy}`}><summary>{b.proxy}: <b className="text-gold">{b.mapped}</b> ({b.raw})</summary>
            {b.blend && <p className="mt-1 text-blueLight">Blend: {b.blend}</p>}
            <p className="whitespace-pre-wrap opacity-80">{b.reasoning.slice(0, 1500)}</p></details>
        ))}
      </section>

      <section className="rounded-xl border border-border bg-card p-4">
        <h2 className="font-semibold text-gold">Trades</h2>
        {d.trades.length === 0 && <p className="text-sm">No trades yet.</p>}
        <table className="mt-2 w-full text-sm"><tbody>
          {d.trades.map((t) => (
            <tr key={t.id} className="border-t border-border">
              <td className="py-1">{etTime(t.opened_at)}</td><td>#{t.account_id}</td><td>{t.symbol} {t.direction} ×{t.qty}</td>
              <td>{t.entry} → {t.exit ?? "open"}</td><td>{t.exit_reason ?? ""}</td>
              <td className="text-gold">{t.pnl ? `${Number(t.pnl) >= 0 ? "▲ +" : "▼ −"}$${Math.abs(Number(t.pnl)).toFixed(2)}` : ""} {t.net_r ? `(${t.net_r}R)` : ""}</td>
              <td><a href={`/replay?trade=${t.id}`}>Replay</a></td>
            </tr>
          ))}
        </tbody></table>
      </section>

      <section className="rounded-xl border border-border bg-card p-4">
        <h2 className="font-semibold text-gold">Signals</h2>
        {d.signals.length === 0 && <p className="text-sm">No signals yet.</p>}
        <table className="mt-2 w-full text-sm"><tbody>
          {d.signals.map((s) => (
            <tr key={s.id} className="border-t border-border">
              <td className="py-1">{etTime(s.at)}</td><td>{s.symbol} {s.profile}</td><td>{s.direction}</td>
              <td className={s.status === "PASS" ? "text-gold" : ""}>{s.status}</td><td>{s.skip_reason ?? ""}</td><td>{s.score ? `score ${Number(s.score).toFixed(0)}` : ""}</td>
            </tr>
          ))}
        </tbody></table>
      </section>
    </div>
  );
}
