import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { usePageTitle } from "../components/usePageTitle";
import { etTime } from "../lib/time";

interface Status {
  mode: "OFF" | "SEMI" | "FULL";
  conservative_mode: boolean;
  broker: string;
  attested_today: boolean;
  entries_blocked_by_time: boolean;
  approvals: { signal_id: number; expires: string }[];
  notices: { level: string; title: string; detail: string; at: string }[];
  rules_error: string | null;
}
interface Preflight { ok: boolean; checks: { check: string; ok: boolean; detail: string }[] }
interface Acct { id: number; label: string; stage: string; armed: boolean; selected: boolean; paused_reason: string | null; eval_mode_effective: boolean; drawdown_type: string; drawdown_check: string | null }
interface Pos { account_id: number; label: string; balance: string; open_pnl: string; mll: string; positions: { symbol: string; qty: number; avg: string }[] }

const btn = "rounded-md border px-3 py-1.5 text-sm font-semibold disabled:opacity-50";

export default function Automation() {
  usePageTitle("Automation");
  const qc = useQueryClient();
  const [err, setErr] = useState("");
  const [kill, setKill] = useState("");
  const st = useQuery({ queryKey: ["automation"], queryFn: () => api<Status>("/api/automation"), refetchInterval: 5000 });
  const pf = useQuery({ queryKey: ["preflight"], queryFn: () => api<Preflight>("/api/automation/preflight", { method: "POST" }), refetchInterval: 30000 });
  const accts = useQuery({ queryKey: ["accounts"], queryFn: () => api<{ accounts: Acct[] }>("/api/accounts") });
  const pos = useQuery({ queryKey: ["positions"], queryFn: () => api<{ accounts: Pos[] }>("/api/positions"), refetchInterval: 5000 });
  const refresh = () => ["automation", "preflight", "accounts", "positions"].forEach((k) => void qc.invalidateQueries({ queryKey: [k] }));
  const run = useMutation({
    mutationFn: (f: () => Promise<unknown>) => f(),
    onMutate: () => setErr(""),
    onSuccess: refresh,
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Request failed"),
  });
  const s = st.data;
  if (!s) return <p role="status">Loading…</p>;

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-gold">Automation</h1>
      {err && <p role="alert" className="rounded-lg border border-gold p-3 text-sm text-goldLight">⚠ {err}</p>}
      {s.rules_error && <p role="alert" className="text-goldLight">⚠ {s.rules_error}</p>}
      {s.conservative_mode && <p className="text-sm text-goldLight">Conservative mode: broker can't report positions back — FULL-AUTO is blocked.</p>}

      <section className="rounded-xl border border-border bg-card p-4">
        <h2 className="font-semibold text-gold">Mode</h2>
        <div className="mt-2 flex flex-wrap gap-2" role="group" aria-label="Automation mode">
          {(["OFF", "SEMI", "FULL"] as const).map((m) => (
            <button key={m} data-testid={`mode-${m}`} disabled={run.isPending}
              className={`${btn} ${s.mode === m ? "border-gold bg-gold/15 text-gold" : "border-blue text-blue"}`}
              onClick={() => run.mutate(() => api("/api/automation", { method: "PUT", body: JSON.stringify({ mode: m }) }))}>
              {m === "SEMI" ? "SEMI-AUTO" : m === "FULL" ? "FULL-AUTO" : "OFF"}
            </button>
          ))}
        </div>
        <p className="mt-2 text-xs">Broker route: {s.broker} · {s.entries_blocked_by_time ? "entries blocked (after flatten time)" : "entries allowed in windows"}</p>
      </section>

      <section className="rounded-xl border border-border bg-card p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-semibold text-gold">Pre-flight {pf.data?.ok ? "✓" : ""}</h2>
          {!s.attested_today && (
            <button className={`${btn} border-blue text-blue`} onClick={() => run.mutate(() => api("/api/attestation", { method: "POST", body: JSON.stringify({ confirm: true }) }))}>
              I hold no positions elsewhere today
            </button>
          )}
        </div>
        <ul className="mt-2 grid gap-1 text-sm sm:grid-cols-2">
          {pf.data?.checks.map((c) => (
            <li key={c.check} data-testid={`pf-${c.check}`} data-ok={c.ok}>
              <span aria-hidden style={{ color: c.ok ? "#22C55E" : "#EF4444" }}>●</span> {c.check.replace(/_/g, " ")}
              {!c.ok && c.detail && <span className="opacity-75"> — {c.detail}</span>}
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-xl border border-border bg-card p-4">
        <h2 className="font-semibold text-gold">Approvals</h2>
        {s.approvals.length === 0 && <p className="text-sm">None waiting.</p>}
        {s.approvals.map((a) => (
          <div key={a.signal_id} className="mt-2 flex flex-wrap items-center gap-2 text-sm">
            <span>Signal #{a.signal_id} · expires {etTime(a.expires)}</span>
            <button className={`${btn} border-gold text-gold`} onClick={() => run.mutate(() => api(`/api/signals/${a.signal_id}/execute`, { method: "POST", body: "{}" }))}>Execute all selected</button>
            <button className={`${btn} border-border text-blue`} onClick={() => run.mutate(() => api(`/api/signals/${a.signal_id}/skip`, { method: "POST" }))}>Skip</button>
          </div>
        ))}
      </section>

      <section className="rounded-xl border border-border bg-card p-4">
        <h2 className="font-semibold text-gold">Accounts</h2>
        <ul className="mt-2 space-y-2 text-sm">
          {accts.data?.accounts.map((a) => {
            const p = pos.data?.accounts.find((x) => x.account_id === a.id);
            return (
              <li key={a.id} className="flex flex-wrap items-center gap-2 rounded-lg border border-border p-2">
                <b className="text-gold">{a.label || a.id}</b><span>{a.stage}</span>
                {a.eval_mode_effective && <span className="text-goldLight">EVAL MODE</span>}
                <span className="inline-flex overflow-hidden rounded-md border border-border" role="group" aria-label="Drawdown type">
                  {(["eod", "intraday"] as const).map((d) => (
                    <button key={d} data-testid={`dd-${a.id}-${d}`}
                      disabled={a.drawdown_type === d}
                      title="Must match your account at Lucid"
                      className={`px-2 py-0.5 text-xs ${a.drawdown_type === d ? "bg-gold/15 text-gold" : "text-blue"} disabled:cursor-default`}
                      onClick={() => run.mutate(() => api(`/api/accounts/${a.id}`, { method: "PATCH", body: JSON.stringify({ drawdown_type: d }) }))}>
                      {d === "eod" ? "EOD trailing" : "Intraday trailing"}
                    </button>
                  ))}
                </span>
                {a.drawdown_check && <span data-testid={`dd-check-${a.id}`} className="text-goldLight">⚠ {a.drawdown_check}</span>}
                {p && <span>bal {p.balance} · open {p.open_pnl} · MLL {p.mll} {p.positions.map((x) => `· ${x.symbol} ${x.qty}`).join(" ")}</span>}
                {a.paused_reason && <span className="text-goldLight">paused: {a.paused_reason}</span>}
                <label className="ml-auto flex items-center gap-1"><input type="checkbox" checked={a.selected}
                  onChange={(e) => run.mutate(() => api(`/api/accounts/${a.id}`, { method: "PATCH", body: JSON.stringify({ selected: e.target.checked }) }))} />selected</label>
                <label className="flex items-center gap-1"><input type="checkbox" checked={a.armed}
                  onChange={(e) => run.mutate(() => api(`/api/accounts/${a.id}`, { method: "PATCH", body: JSON.stringify({ armed: e.target.checked }) }))} />armed</label>
                <button className={`${btn} border-border text-blue`} onClick={() => run.mutate(() => api(`/api/accounts/${a.id}/flatten`, { method: "POST" }))}>Flatten</button>
              </li>
            );
          })}
        </ul>
        <button className={`${btn} mt-3 border-blue text-blue`} onClick={() => {
          const label = window.prompt("Paper account name");
          if (label) run.mutate(() => api("/api/accounts", { method: "POST", body: JSON.stringify({ label, stage: "EVAL" }) }));
        }}>+ Add paper account</button>
      </section>

      <section className="rounded-xl border border-gold bg-card p-4">
        <h2 className="font-semibold text-gold">Kill switch</h2>
        <p className="text-xs">Flattens everything, disarms all accounts and turns automation OFF. Type KILL.</p>
        <div className="mt-2 flex gap-2">
          <input aria-label="Type KILL" value={kill} onChange={(e) => setKill(e.target.value)} className="w-28" />
          <button data-testid="kill" disabled={kill !== "KILL"} className={`${btn} border-gold text-gold`}
            onClick={() => run.mutate(() => api("/api/kill-switch", { method: "POST", body: JSON.stringify({ confirm: "KILL" }) }))}>KILL SWITCH</button>
        </div>
      </section>

      <section className="text-xs">
        <h2 className="font-semibold text-gold">Recent notices</h2>
        {s.notices.slice().reverse().map((n, i) => <p key={i}>{etTime(n.at)} · {n.title} {n.detail}</p>)}
      </section>
    </div>
  );
}
