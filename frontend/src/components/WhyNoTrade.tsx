import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { skipRows } from "../lib/insights";

interface Skips { date: string; counts: Record<string, number>; avg_20: Record<string, number>; sessions_in_avg: number }

export default function WhyNoTrade() {
  const q = useQuery({ queryKey: ["skips"], queryFn: () => api<Skips>("/api/signals/skips"), refetchInterval: 15000 });
  const d = q.data;
  const rows = d ? skipRows(d.counts, d.avg_20) : [];
  return (
    <section data-testid="why-no-trade" className="rounded-xl border border-border bg-card p-4">
      <h2 className="font-semibold text-gold">Why no trade?</h2>
      {!d && <p className="text-sm" role="status">Loading…</p>}
      {d && rows.length === 0 && <p className="text-sm">No skipped signals today.</p>}
      {rows.length > 0 && (
        <table className="mt-2 w-full text-sm">
          <thead><tr className="text-left text-xs text-blueLight"><th>Reason</th><th>Today</th><th>20-session avg</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.code} className="border-t border-border">
                <td className="py-1">{r.label}{r.label !== r.code && <span className="ml-2 text-xs opacity-60">{r.code}</span>}</td>
                <td className="font-semibold text-gold">{r.count}</td>
                <td>{d && d.sessions_in_avg > 0 ? r.avg.toFixed(1) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
