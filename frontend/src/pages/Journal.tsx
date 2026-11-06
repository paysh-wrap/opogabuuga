import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { usePageTitle } from "../components/usePageTitle";
import { etDateTime } from "../lib/time";

interface Row { id: number; at: string; actor: string; action: string; entity: string; payload: Record<string, unknown> }
interface Resp { logs: Row[]; actions: string[]; chain_ok: boolean; chain_first_bad_id: number | null }

const esc = (v: string) => (/[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v);
export function toCsv(rows: Row[]): string {
  const head = "id,at,actor,action,entity,payload";
  return [head, ...rows.map((r) => [String(r.id), r.at, r.actor, r.action, r.entity, JSON.stringify(r.payload)].map(esc).join(","))].join("\n");
}

export default function Journal() {
  usePageTitle("Journal & Logs");
  const [q, setQ] = useState("");
  const [action, setAction] = useState("");
  const [since, setSince] = useState("");
  const [until, setUntil] = useState("");
  const params = new URLSearchParams({ limit: "500" });
  if (q) params.set("q", q);
  if (action) params.set("action", action);
  if (since) params.set("since", since);
  if (until) params.set("until", until);
  const url = `/api/logs?${params.toString()}`;
  const res = useQuery({ queryKey: ["logs", url], queryFn: () => api<Resp>(url) });

  function exportCsv() {
    if (!res.data) return;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([toCsv(res.data.logs)], { type: "text/csv" }));
    a.download = "paytience-audit-log.csv";
    a.click();
    URL.revokeObjectURL(a.href);
  }
  const inp = "rounded border border-border bg-bg px-2 py-1 text-sm text-blueLight";
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-gold">Journal &amp; Logs</h1>
      <p className="text-sm">Append-only audit log of everything the app and you did. Hash chain:{" "}
        {res.data ? (res.data.chain_ok ? <b className="text-gold" data-testid="chain">intact</b>
          : <b className="text-goldLight" data-testid="chain">BROKEN at entry {res.data.chain_first_bad_id}</b>) : "…"}</p>
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-xs">Search<br /><input aria-label="Search" className={inp} value={q} onChange={(e) => setQ(e.target.value)} /></label>
        <label className="text-xs">Action<br />
          <select aria-label="Action" className={inp} value={action} onChange={(e) => setAction(e.target.value)}>
            <option value="">All</option>
            {res.data?.actions.map((a) => <option key={a}>{a}</option>)}
          </select></label>
        <label className="text-xs">From<br /><input type="date" aria-label="From" className={inp} value={since} onChange={(e) => setSince(e.target.value)} /></label>
        <label className="text-xs">To<br /><input type="date" aria-label="To" className={inp} value={until} onChange={(e) => setUntil(e.target.value)} /></label>
        <button onClick={exportCsv} disabled={!res.data?.logs.length}
          className="rounded-md border border-blue px-3 py-1 text-sm font-semibold text-blue disabled:opacity-50">Export CSV</button>
      </div>
      {res.isLoading && <p role="status">Loading…</p>}
      {res.error && <p role="alert" className="text-goldLight">⚠ Could not load logs: {String(res.error.message)}</p>}
      {res.data?.logs.length === 0 && <p className="rounded-xl border border-border bg-card p-4 text-sm">No log entries match.</p>}
      {!!res.data?.logs.length && (
        <div className="overflow-x-auto rounded-xl border border-border bg-card p-3">
          <table className="w-full text-sm">
            <thead className="text-left text-gold"><tr><th>When</th><th>Actor</th><th>Action</th><th>Entity</th><th>Details</th></tr></thead>
            <tbody>
              {res.data.logs.map((r) => (
                <tr key={r.id} data-testid={`log-${r.id}`} className="border-t border-border align-top">
                  <td className="whitespace-nowrap py-1">{etDateTime(r.at)}</td><td>{r.actor}</td>
                  <td className="text-gold">{r.action}</td><td>{r.entity}</td>
                  <td className="break-all font-mono text-xs">{JSON.stringify(r.payload)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
