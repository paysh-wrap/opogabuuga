import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { usePageTitle } from "../components/usePageTitle";
import { etTime } from "../lib/time";

interface Sig { id: number; symbol: string; profile: string; direction: string; status: string; skip_reason: string | null; score: string | null; at: string }
interface Tr { id: number; account_id: number; symbol: string; direction: string; qty: number; entry: string; exit: string | null; pnl: string | null; net_r: string | null; exit_reason: string | null; opened_at: string }

export default function Today() {
  usePageTitle("Today");
  const q = useQuery({ queryKey: ["today"], queryFn: () => api<{ signals: Sig[]; trades: Tr[] }>("/api/today"), refetchInterval: 10000 });
  const d = q.data;
  if (!d) return <p role="status">Loading…</p>;
  const net = d.trades.reduce((s, t) => s + Number(t.pnl ?? 0), 0);
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-gold">Today</h1>
      <p className="text-sm">{d.signals.length} signals · {d.signals.filter((s) => s.status === "PASS").length} passed · {d.trades.length} trades · net{" "}
        <b className="text-gold">{net > 0 ? "▲ +" : net < 0 ? "▼ −" : ""}${Math.abs(net).toFixed(2)}</b></p>

      <section className="rounded-xl border border-border bg-card p-4">
        <h2 className="font-semibold text-gold">Trades</h2>
        {d.trades.length === 0 && <p className="text-sm">No trades yet.</p>}
        <table className="mt-2 w-full text-sm"><tbody>
          {d.trades.map((t) => (
            <tr key={t.id} className="border-t border-border">
              <td className="py-1">{etTime(t.opened_at)}</td><td>#{t.account_id}</td><td>{t.symbol} {t.direction} ×{t.qty}</td>
              <td>{t.entry} → {t.exit ?? "open"}</td><td>{t.exit_reason ?? ""}</td>
              <td className="text-gold">{t.pnl ? `${Number(t.pnl) >= 0 ? "▲ +" : "▼ −"}$${Math.abs(Number(t.pnl)).toFixed(2)}` : ""} {t.net_r ? `(${t.net_r}R)` : ""}</td>
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
