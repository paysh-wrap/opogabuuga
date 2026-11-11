import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { usePageTitle } from "../components/usePageTitle";
import { PayoutConsistencyNote, type PayoutConsistencyView } from "../components/PayoutConsistency";

interface Acct {
  id: number;
  broker_account_id: string;
  label: string;
  stage: string;
  paper: boolean;
  drawdown_type: "eod" | "intraday";
  drawdown_check: string | null;
  dll_enabled: boolean;
  eval_mode: "inherit" | "on" | "off";
  eval_mode_effective: boolean;
  armed: boolean;
  selected: boolean;
  priority: number;
  mll_locked: boolean;
  paused_reason: string | null;
  mode_override?: "inherit" | "SEMI" | "OFF";
  consistency_pct?: string | null;
  purchased_at?: string | null;
  payout_consistency?: PayoutConsistencyView | null;
}
interface Dash { accounts: { id: number; idle_days?: number; idle_alert_days?: number }[] }

export const LUCID_URL = "https://lucidtrading.com/"; // opens Lucid's own site; the app never automates it (§1.3)
const btn = "rounded-md border px-2.5 py-1 text-xs font-semibold disabled:opacity-50";

export default function Accounts() {
  usePageTitle("Accounts");
  const qc = useQueryClient();
  const [err, setErr] = useState("");
  const q = useQuery({ queryKey: ["accounts"], queryFn: () => api<{ accounts: Acct[] }>("/api/accounts"), refetchInterval: 15000 });
  const dash = useQuery({ queryKey: ["dashboard"], queryFn: () => api<Dash>("/api/dashboard"), refetchInterval: 30000 });
  const logs = useQuery({ queryKey: ["account-history"], queryFn: () => api<{ logs: { id: number; at: string; actor: string; action: string; entity: string; payload: unknown }[] }>("/api/logs?limit=500"), staleTime: 30_000 });
  const run = useMutation({
    mutationFn: (f: () => Promise<unknown>) => f(),
    onMutate: () => setErr(""),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["accounts"] }),
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Request failed"),
  });
  if (q.isLoading) return <p role="status">Loading…</p>;
  if (q.error || !q.data) return <p role="alert">Cannot load accounts: {q.error instanceof Error ? q.error.message : "unknown error"}</p>;

  const list = q.data.accounts;
  const trading = list.filter((a) => a.selected).length;
  const select = (count: number, order: number[] = []) =>
    run.mutate(() => api("/api/accounts/selection", { method: "PUT", body: JSON.stringify({ count, order }) }));
  const move = (i: number, d: -1 | 1) => {
    const ids = list.map((a) => a.id);
    const j = i + d;
    if (j < 0 || j >= ids.length) return;
    [ids[i], ids[j]] = [ids[j]!, ids[i]!];
    select(trading || 1, ids);
  };
  const patch = (id: number, body: object) => run.mutate(() => api(`/api/accounts/${id}`, { method: "PATCH", body: JSON.stringify(body) }));
  const history = (a: Acct) => (logs.data?.logs ?? []).filter((l) => l.entity === String(a.id) || l.entity === a.broker_account_id);
  const idle = (id: number) => dash.data?.accounts.find((a) => a.id === id);

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-gold">Accounts</h1>
      {err && <p role="alert" className="rounded-lg border border-gold p-3 text-sm text-goldLight">⚠ {err}</p>}
      <section className="rounded-xl border border-border bg-card p-4">
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <span data-testid="trading-n">Trading <b className="text-gold">{trading} of {list.length}</b></span>
          <span className="inline-flex gap-1" role="group" aria-label="Accounts to trade">
            {[1, 2, 3, 4, 5].map((n) => (
              <button key={n} data-testid={`sel-${n}`} disabled={run.isPending || list.length === 0}
                className={`${btn} ${trading === n ? "border-gold bg-gold/15 text-gold" : "border-blue text-blue"}`}
                onClick={() => select(n)}>{n}</button>
            ))}
          </span>
          <a href={LUCID_URL} target="_blank" rel="noreferrer" className="ml-auto text-blue underline">Open Lucid dashboard ↗</a>
        </div>
        <p className="mt-2 text-xs">The first N accounts in priority order are selected. An account trades only if selected AND armed AND passing every check.
          {trading > 1 && ` ${trading} accounts on one signal = ${trading}× correlated exposure.`}</p>
      </section>

      {list.length === 0 && <p className="text-sm">No accounts yet — add one on the Automation page.</p>}
      <ul className="space-y-3">
        {list.map((a, i) => {
          const d = idle(a.id);
          return (
            <li key={a.id} data-testid={`account-${a.id}`} className="rounded-xl border border-border bg-card p-4 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <b className="text-gold">{a.label || a.broker_account_id}</b>
                <span>{a.stage}</span>
                <span className={`rounded border px-1 text-xs ${a.paper ? "border-border text-blue" : "border-gold text-gold"}`}>{a.paper ? "APP PAPER" : "LUCID"}</span>
                {a.mll_locked && <span className="rounded border border-gold px-1 text-xs text-gold">MLL LOCKED</span>}
                {a.eval_mode_effective && <span className="rounded border border-gold px-1 text-xs text-goldLight">EVAL MODE</span>}
                {a.paused_reason && <span className="text-goldLight">paused: {a.paused_reason}</span>}
                <span className="ml-auto text-xs">priority #{i + 1}</span>
                <button aria-label={`Move ${a.label} up`} className={`${btn} border-border text-blue`} disabled={i === 0 || run.isPending} onClick={() => move(i, -1)}>↑</button>
                <button aria-label={`Move ${a.label} down`} className={`${btn} border-border text-blue`} disabled={i === list.length - 1 || run.isPending} onClick={() => move(i, 1)}>↓</button>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-3">
                <span className="inline-flex overflow-hidden rounded-md border border-border" role="group" aria-label={`Drawdown type of ${a.label}`}>
                  {(["eod", "intraday"] as const).map((t) => (
                    <button key={t} data-testid={`dd-${a.id}-${t}`} disabled={a.drawdown_type === t || run.isPending}
                      title="Must match your account at Lucid"
                      className={`px-2 py-0.5 text-xs ${a.drawdown_type === t ? "bg-gold/15 text-gold" : "text-blue"}`}
                      onClick={() => patch(a.id, { drawdown_type: t })}>{t === "eod" ? "EOD trailing" : "Intraday trailing"}</button>
                  ))}
                </span>
                <span>DLL {a.dll_enabled ? "ON" : "OFF"}</span>
                <span data-testid={`cons-${a.id}`} title="Largest single day as % of total profit (Lucid consistency rule for this stage)">
                  Consistency {a.consistency_pct ? `${Number(a.consistency_pct)}% max day` : "none"}
                </span>
                <label className="flex items-center gap-1" title="Per-account automation: can only be stricter than the global mode">Mode
                  <select data-testid={`override-${a.id}`} value={a.mode_override ?? "inherit"} disabled={run.isPending}
                    onChange={(e) => patch(a.id, { mode_override: e.target.value })}>
                    <option value="inherit">inherit (global)</option><option value="SEMI">SEMI (approve each)</option><option value="OFF">OFF (no automation)</option>
                  </select>
                </label>
                {a.stage === "EVAL" && (
                  <label className="flex items-center gap-1">Eval Mode
                    <select data-testid={`eval-${a.id}`} value={a.eval_mode} disabled={run.isPending}
                      onChange={(e) => { const override = e.target.value; run.mutate(() => api(`/api/accounts/${a.id}/eval-mode`, { method: "PATCH", body: JSON.stringify({ override }) })); }}>
                      <option value="inherit">inherit</option><option value="on">on</option><option value="off">off</option>
                    </select>
                  </label>
                )}
                <label className="flex items-center gap-1"><input type="checkbox" checked={a.selected} disabled={run.isPending}
                  onChange={(e) => patch(a.id, { selected: e.target.checked })} />selected</label>
                <label className="flex items-center gap-1"><input type="checkbox" checked={a.armed} disabled={run.isPending}
                  onChange={(e) => patch(a.id, { armed: e.target.checked })} />armed</label>
                {d?.idle_days !== undefined && (
                  <span data-testid={`idle-${a.id}`}>
                    Last trade {d.idle_days}d ago{d.idle_alert_days !== undefined && d.idle_days >= d.idle_alert_days && <b className="text-goldLight"> · inactivity alert</b>}
                  </span>
                )}
              </div>
              <details className="mt-2 text-xs" data-testid={`history-${a.id}`}>
                <summary className="cursor-pointer text-blue">History</summary>
                {logs.isLoading && <p role="status">Loading…</p>}
                {logs.data && history(a).length === 0 && <p>No recorded changes yet.</p>}
                {history(a).slice(0, 30).map((l) => (
                  <p key={l.id}>{new Date(l.at).toLocaleString()} · {l.actor} · <b className="text-gold">{l.action}</b> {l.payload ? JSON.stringify(l.payload).slice(0, 120) : ""}</p>
                ))}
              </details>
              {a.stage === "FUNDED" && a.payout_consistency && (
                <div className="mt-2 space-y-1">
                  <PayoutConsistencyNote v={a.payout_consistency} id={a.id} />
                  <label className="flex flex-wrap items-center gap-2 text-xs">Purchased / last reset at Lucid
                    <input type="date" data-testid={`purchased-${a.id}`} aria-label={`Purchase or reset date of ${a.label}`}
                      defaultValue={a.purchased_at ? a.purchased_at.slice(0, 10) : ""} disabled={run.isPending}
                      onChange={(e) => e.target.value
                        ? patch(a.id, { purchased_at: `${e.target.value}T12:00:00-05:00` })
                        : patch(a.id, { clear_purchased_at: true })} />
                    <span>(decides the 40% or 35% limit; unknown = 35% until you enter it)</span>
                  </label>
                </div>
              )}
              {a.drawdown_check && <p className="mt-2 text-xs text-goldLight">⚠ {a.drawdown_check}</p>}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
