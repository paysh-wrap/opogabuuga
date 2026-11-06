import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { calendarWeeks, signedUsd, type DayPnl } from "../lib/insights";

interface Series { days: DayPnl[]; weeks: { week_start: string; pnl: string }[]; total: string }
interface EvalView { largest_day: string; largest_pnl: string; limit_pct: string; cap: string; largest_pct: string | null }
interface Acct extends Series { id: number; label: string; stage: string | null; eval?: EvalView }
interface Daily { household: Series; accounts: Acct[] }

const DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function Grid({ series, largest, cap }: { series: Series; largest?: string; cap?: number }) {
  const weeks = calendarWeeks(series.days);
  const max = Math.max(1, ...series.days.map((d) => Math.abs(Number(d.pnl))));
  if (weeks.length === 0) return <p className="text-sm">No closed trades yet.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[34rem] border-separate border-spacing-1 text-center text-xs">
        <thead><tr>{DOW.map((d) => <th key={d} className="font-normal text-blueLight">{d}</th>)}<th className="font-normal text-blueLight">Week</th></tr></thead>
        <tbody>
          {weeks.map((w) => (
            <tr key={w.start}>
              {w.days.map((c, i) => {
                const n = Number(c?.pnl ?? 0);
                const a = c ? 0.12 + 0.45 * (Math.abs(n) / max) : 0;
                const bg = !c ? "transparent" : n >= 0 ? `rgba(212,175,55,${a})` : `rgba(59,130,246,${a})`;
                const isLargest = c != null && c.date === largest;
                return (
                  <td key={i} title={c ? `${c.date}: ${signedUsd(n)}` : ""} data-testid={c ? `cal-${c.date}` : undefined}
                    className={`rounded-md px-1 py-2 ${isLargest ? "border-2 border-gold" : "border border-border"}`} style={{ background: bg }}>
                    {c && <><div className="opacity-70">{c.date.slice(5)}</div><div className="font-semibold text-gold">{signedUsd(n)}</div>
                      {isLargest && <div className="text-goldLight">largest day</div>}</>}
                  </td>
                );
              })}
              <td className="font-semibold text-gold">{signedUsd(w.total)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {cap != null && <p className="mt-1 text-xs text-blueLight">Consistency line: no day above ${cap.toFixed(0)} (cap).</p>}
    </div>
  );
}

export default function PnlCalendar() {
  const q = useQuery({ queryKey: ["pnl-daily"], queryFn: () => api<Daily>("/api/pnl/daily"), refetchInterval: 30000 });
  const d = q.data;
  return (
    <section data-testid="pnl-calendar" className="space-y-4 rounded-xl border border-border bg-card p-4">
      <h2 className="font-semibold text-gold">Daily P&amp;L calendar</h2>
      {!d && <p className="text-sm" role="status">Loading…</p>}
      {d && (
        <>
          <div>
            <h3 className="text-sm text-blueLight">Household · total <b className="text-gold">{signedUsd(Number(d.household.total))}</b></h3>
            <Grid series={d.household} />
          </div>
          {d.accounts.map((a) => (
            <div key={a.id}>
              <h3 className="text-sm text-blueLight">{a.label} ({a.stage}) · total <b className="text-gold">{signedUsd(Number(a.total))}</b>
                {a.eval && <> · largest day {signedUsd(Number(a.eval.largest_pnl))}{a.eval.largest_pct != null ? ` = ${Number(a.eval.largest_pct).toFixed(0)}% of profit` : ""} (limit {a.eval.limit_pct}%)</>}
              </h3>
              <Grid series={a} largest={a.eval?.largest_day} cap={a.eval ? Number(a.eval.cap) : undefined} />
            </div>
          ))}
        </>
      )}
    </section>
  );
}
