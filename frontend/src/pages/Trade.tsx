import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { usePageTitle } from "../components/usePageTitle";
import { etTime } from "../lib/time";

interface Status {
  mode: string;
  broker: string;
  attested_today: boolean;
  entries_blocked_by_time: boolean;
  approvals: { signal_id: number; expires: string }[];
  rules_error: string | null;
}
interface Preflight { ok: boolean; checks: { check: string; ok: boolean; detail: string }[] }
interface Acct { id: number; label: string; stage: string; armed: boolean; selected: boolean; paused_reason: string | null; paper: boolean }
interface Pos { account_id: number; label: string; balance?: string; open_pnl?: string; mll?: string; positions: { symbol: string; qty: number; avg: string }[]; error?: string }

const FLATTEN_PHRASE = "FLATTEN ALL"; // must match backend FLATTEN_PHRASE
const btn = "rounded-md border px-3 py-1.5 text-sm font-semibold disabled:opacity-50";
const sign = (v: string | undefined) => {
  const n = Number(v ?? 0);
  return `${n >= 0 ? "▲ +" : "▼ −"}$${Math.abs(n).toFixed(2)}`;
};

export default function Trade() {
  usePageTitle("Trade");
  const qc = useQueryClient();
  const [err, setErr] = useState("");
  const [typed, setTyped] = useState("");
  const [attest, setAttest] = useState(false);
  const st = useQuery({ queryKey: ["automation"], queryFn: () => api<Status>("/api/automation"), refetchInterval: 5000 });
  const pf = useQuery({ queryKey: ["preflight"], queryFn: () => api<Preflight>("/api/automation/preflight", { method: "POST" }), refetchInterval: 30000 });
  const accts = useQuery({ queryKey: ["accounts"], queryFn: () => api<{ accounts: Acct[] }>("/api/accounts"), refetchInterval: 10000 });
  const pos = useQuery({ queryKey: ["positions"], queryFn: () => api<{ accounts: Pos[] }>("/api/positions"), refetchInterval: 5000 });
  const refresh = () => ["automation", "preflight", "accounts", "positions"].forEach((k) => void qc.invalidateQueries({ queryKey: [k] }));
  const run = useMutation({
    mutationFn: (f: () => Promise<unknown>) => f(),
    onMutate: () => setErr(""),
    onSuccess: refresh,
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Request failed"),
  });
  const patch = (id: number, body: object) => run.mutate(() => api(`/api/accounts/${id}`, { method: "PATCH", body: JSON.stringify(body) }));

  if (st.isLoading) return <p role="status">Loading…</p>;
  if (st.error || !st.data) return <p role="alert">Cannot load trading status: {st.error instanceof Error ? st.error.message : "unknown error"}</p>;
  const s = st.data;
  const open = pos.data?.accounts.flatMap((p) => p.positions.map((x) => ({ ...x, label: p.label, account_id: p.account_id }))) ?? [];

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-gold">Trade</h1>
      {err && <p role="alert" className="rounded-lg border border-gold p-3 text-sm text-goldLight">⚠ {err}</p>}
      {s.rules_error && <p role="alert" className="text-goldLight">⚠ {s.rules_error}</p>}

      <section className="rounded-xl border border-border bg-card p-4">
        <h2 className="font-semibold text-gold">Mode</h2>
        <p data-testid="trade-mode" className="mt-1 text-sm">
          Automation <b className="text-gold">{s.mode}</b> · broker {s.broker} · {s.entries_blocked_by_time ? "entries blocked (after flatten time)" : "entries allowed in windows"}
          {" "}· change the mode on the <Link to="/automation" className="text-blue underline">Automation</Link> page.
        </p>
      </section>

      <section className="rounded-xl border border-border bg-card p-4">
        <h2 className="font-semibold text-gold">Approvals</h2>
        {s.approvals.length === 0 && <p className="text-sm">None waiting{s.mode.startsWith("SEMI") ? "" : " (approvals appear in SEMI-AUTO)"}.</p>}
        {s.approvals.map((a) => (
          <div key={a.signal_id} data-testid={`approval-${a.signal_id}`} className="mt-2 flex flex-wrap items-center gap-2 text-sm">
            <Link to="/signals" className="text-blue underline">Signal #{a.signal_id}</Link>
            <span>expires {etTime(a.expires)}</span>
            <button className={`${btn} border-gold text-gold`} disabled={run.isPending}
              onClick={() => run.mutate(() => api(`/api/signals/${a.signal_id}/execute`, { method: "POST", body: "{}" }))}>Execute all selected</button>
            <button className={`${btn} border-border text-blue`} disabled={run.isPending}
              onClick={() => run.mutate(() => api(`/api/signals/${a.signal_id}/skip`, { method: "POST" }))}>Skip</button>
          </div>
        ))}
        <p className="mt-2 text-xs">Executing re-runs every check on the server. Manual order ticket: not available yet (no manual-order endpoint).</p>
      </section>

      <section className="rounded-xl border border-border bg-card p-4">
        <h2 className="font-semibold text-gold">Positions</h2>
        {pos.isLoading && <p role="status" className="text-sm">Loading…</p>}
        {pos.error && <p role="alert" className="text-sm text-goldLight">⚠ Cannot load positions.</p>}
        {pos.data && open.length === 0 && <p className="text-sm">No open positions.</p>}
        {open.length > 0 && (
          <table className="mt-2 w-full text-sm"><tbody>
            {open.map((x) => (
              <tr key={`${x.account_id}-${x.symbol}`} data-testid={`position-${x.account_id}`} className="border-t border-border">
                <td className="py-1 text-gold">{x.label}</td><td>{x.symbol}</td>
                <td>{x.qty > 0 ? "▲ LONG" : "▼ SHORT"} {Math.abs(x.qty)}</td><td>avg {x.avg}</td>
              </tr>
            ))}
          </tbody></table>
        )}
        <p className="mt-2 text-xs">Working orders are not reported by the broker adapter yet; only positions are shown.</p>
      </section>

      <section className="rounded-xl border border-border bg-card p-4">
        <h2 className="font-semibold text-gold">Accounts</h2>
        {accts.data?.accounts.length === 0 && <p className="text-sm">No accounts yet — add one on the <Link to="/accounts" className="text-blue underline">Accounts</Link> page.</p>}
        <ul className="mt-2 space-y-2 text-sm">
          {accts.data?.accounts.map((a) => {
            const p = pos.data?.accounts.find((x) => x.account_id === a.id);
            return (
              <li key={a.id} data-testid={`acct-${a.id}`} className="flex flex-wrap items-center gap-2 rounded-lg border border-border p-2">
                <b className="text-gold">{a.label || a.id}</b><span>{a.stage}</span>
                {p?.balance && <span>bal {p.balance} · open {sign(p.open_pnl)} · MLL {p.mll}</span>}
                {p?.error && <span className="text-goldLight">⚠ {p.error}</span>}
                {a.paused_reason && <span className="text-goldLight">paused: {a.paused_reason}</span>}
                <button data-testid={`arm-${a.id}`} className={`${btn} ml-auto ${a.armed ? "border-gold bg-gold/15 text-gold" : "border-blue text-blue"}`}
                  disabled={run.isPending || (!a.armed && !s.attested_today)}
                  title={!a.armed && !s.attested_today ? "Attest first (external positions)" : undefined}
                  onClick={() => patch(a.id, { armed: !a.armed })}>{a.armed ? "Disarm" : "Arm"}</button>
                <button className={`${btn} border-border text-blue`} disabled={run.isPending}
                  onClick={() => run.mutate(() => api(`/api/accounts/${a.id}/flatten`, { method: "POST" }))}>Flatten</button>
              </li>
            );
          })}
        </ul>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <input aria-label={`Type ${FLATTEN_PHRASE}`} placeholder={FLATTEN_PHRASE} value={typed} onChange={(e) => setTyped(e.target.value)} className="w-36" />
          <button data-testid="flatten-all" disabled={typed !== FLATTEN_PHRASE || run.isPending} className={`${btn} border-gold text-gold`}
            onClick={() => run.mutate(async () => { await api("/api/flatten-all", { method: "POST", body: JSON.stringify({ confirm: typed }) }); setTyped(""); })}>FLATTEN ALL</button>
        </div>
      </section>

      <section className="rounded-xl border border-border bg-card p-4">
        <h2 className="font-semibold text-gold">Pre-flight {pf.data?.ok ? "✓" : ""}</h2>
        {pf.isLoading && <p role="status" className="text-sm">Running checks…</p>}
        {pf.error && <p role="alert" className="text-sm text-goldLight">⚠ Pre-flight could not run.</p>}
        <ul className="mt-2 grid gap-1 text-sm sm:grid-cols-2">
          {pf.data?.checks.map((c) => (
            <li key={c.check} data-testid={`pf-${c.check}`} data-ok={c.ok}>
              <span aria-hidden style={{ color: c.ok ? "#22C55E" : "#EF4444" }}>●</span> {c.check.replace(/_/g, " ")}
              {!c.ok && c.detail && <span className="opacity-75"> — {c.detail}</span>}
            </li>
          ))}
        </ul>
        <div className="mt-3 border-t border-border pt-3 text-sm">
          {s.attested_today ? <p data-testid="attested">✓ External-positions attestation done for today.</p> : (
            <label className="flex items-start gap-2">
              <input type="checkbox" checked={attest} onChange={(e) => setAttest(e.target.checked)} />
              <span>I hold no open positions at other firms/platforms that could hedge or correlate with these accounts.</span>
            </label>
          )}
          {!s.attested_today && (
            <button data-testid="attest" disabled={!attest || run.isPending} className={`${btn} mt-2 border-blue text-blue`}
              onClick={() => run.mutate(() => api("/api/attestation", { method: "POST", body: JSON.stringify({ confirm: true }) }))}>Attest for today</button>
          )}
        </div>
      </section>
    </div>
  );
}
