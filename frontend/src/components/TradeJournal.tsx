import { Fragment, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { etDateTime } from "../lib/time";

export interface JRow {
  id: number; account: string; symbol: string; direction: string; qty: number; entry: string; exit: string | null;
  pnl_usd: string | null; net_r: string | null; exit_reason: string | null; opened_at: string; closed_at: string | null;
  mode: string; profile: string | null; score: string | null; snapshot: Record<string, unknown> | null;
}
interface Resp { trades: JRow[]; summary: { count: number; closed: number; wins: number; net_pnl: string }; symbols: string[] }

const inp = "rounded border border-border bg-bg px-2 py-1 text-sm text-blueLight";
const pnl = (v: string | null) => (v == null ? "open" : `${Number(v) >= 0 ? "▲ +" : "▼ −"}$${Math.abs(Number(v)).toFixed(2)}`);

export function journalQuery(f: Record<string, string>, csv = false): string {
  const p = new URLSearchParams();
  Object.entries(f).forEach(([k, v]) => v && p.set(k, v));
  if (csv) p.set("format", "csv");
  return `/api/journal?${p.toString()}`;
}

/** Trade journal (§18 Journal & Logs): search, filters, signal snapshot, CSV export from the server. */
export default function TradeJournal() {
  const [f, setF] = useState({ q: "", symbol: "", direction: "", result: "", since: "", until: "" });
  const [open, setOpen] = useState<number | null>(null);
  const url = journalQuery(f);
  const res = useQuery({ queryKey: ["journal", url], queryFn: () => api<Resp>(url) });
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  const s = res.data?.summary;
  return (
    <section className="space-y-3 rounded-xl border border-border bg-card p-4" data-testid="trade-journal">
      <h2 className="font-semibold text-gold">Trade journal</h2>
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-xs">Search<br /><input aria-label="Journal search" className={inp} value={f.q} onChange={set("q")} /></label>
        <label className="text-xs">Market<br /><select aria-label="Journal market" className={inp} value={f.symbol} onChange={set("symbol")}>
          <option value="">All</option>{res.data?.symbols?.map((x) => <option key={x}>{x}</option>)}</select></label>
        <label className="text-xs">Side<br /><select aria-label="Journal side" className={inp} value={f.direction} onChange={set("direction")}>
          <option value="">All</option><option>LONG</option><option>SHORT</option></select></label>
        <label className="text-xs">Result<br /><select aria-label="Journal result" className={inp} value={f.result} onChange={set("result")}>
          <option value="">All</option><option value="win">Wins</option><option value="loss">Losses</option><option value="open">Open</option></select></label>
        <label className="text-xs">From<br /><input type="date" aria-label="Journal from" className={inp} value={f.since} onChange={set("since")} /></label>
        <label className="text-xs">To<br /><input type="date" aria-label="Journal to" className={inp} value={f.until} onChange={set("until")} /></label>
        <a data-testid="journal-csv" href={journalQuery(f, true)} download="paytience-journal.csv"
          className="rounded-md border border-blue px-3 py-1 text-sm font-semibold text-blue">Export CSV</a>
      </div>
      {res.isLoading && <p role="status">Loading…</p>}
      {res.error && <p role="alert" className="text-goldLight">⚠ Could not load trades: {String(res.error.message)}</p>}
      {s && <p className="text-sm" data-testid="journal-summary">{s.count} trades · {s.closed} closed · {s.wins} wins · net <b className="text-gold">{pnl(s.net_pnl)}</b></p>}
      {res.data?.trades?.length === 0 && <p className="text-sm">No trades match.</p>}
      {!!res.data?.trades?.length && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-gold"><tr><th>Opened</th><th>Account</th><th>Market</th><th>Side</th><th>Qty</th><th>Entry</th><th>Exit</th><th>P&amp;L</th><th>R</th><th>Reason</th><th /></tr></thead>
            <tbody>
              {res.data.trades.map((t) => (
                <Fragment key={t.id}>
                  <tr data-testid={`jt-${t.id}`} className="border-t border-border">
                    <td className="whitespace-nowrap py-1">{etDateTime(t.opened_at)}</td><td>{t.account}</td><td>{t.symbol}</td>
                    <td>{t.direction === "LONG" ? "▲ LONG" : "▼ SHORT"}</td><td>{t.qty}</td><td>{t.entry}</td><td>{t.exit ?? "—"}</td>
                    <td className="text-gold">{pnl(t.pnl_usd)}</td><td>{t.net_r ?? "—"}</td><td>{t.exit_reason ?? "—"} <span className="text-xs">{t.mode}</span></td>
                    <td>{t.snapshot && <button className="text-xs text-blue underline" onClick={() => setOpen(open === t.id ? null : t.id)}>Snapshot</button>}</td>
                  </tr>
                  {open === t.id && (
                    <tr key={`${t.id}-s`}><td colSpan={11} className="break-all pb-2 font-mono text-xs" data-testid={`snap-${t.id}`}>
                      score {t.score ?? "—"} · profile {t.profile ?? "—"} · {JSON.stringify(t.snapshot)}</td></tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
