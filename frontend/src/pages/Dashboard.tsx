import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { usePageTitle } from "../components/usePageTitle";
import Markets from "../components/Markets";
import WhyNoTrade from "../components/WhyNoTrade";
import { band, meters } from "../lib/insights";

interface Acct {
  id: number; label: string; stage: string; paper: boolean; armed: boolean; paused: string | null; error?: string;
  balance?: string; open_pnl?: string; mll?: string | null; to_mll?: string | null; kill_at?: string; today_pnl?: string;
  trades_today?: number; dll_left?: string | null; consistency_cap?: string | null; consistency_stop?: string | null;
  target_left?: string | null; mll_locked?: boolean; fast_profit_pct?: string; fast_warn_pct?: string; fast_limit_pct?: string; fast_hold_s?: number; idle_days?: number; idle_alert_days?: number; idle_delete_days?: number;
  max_loss?: string; dll_limit?: string | null;
}
interface Dash { session: string; mode: string; bias: Record<string, string>; accounts: Acct[] }

const money = (v?: string | null) => (v == null ? "—" : `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })}`);
function Pnl({ v }: { v?: string }) {
  const n = Number(v ?? 0);
  return <span className="font-semibold text-gold">{n > 0 ? "▲ +" : n < 0 ? "▼ −" : ""}{money(String(Math.abs(n)))}</span>;
}
function Meters({ a }: { a: Acct }) {
  const ms = meters({ ...a, stage: a.stage });
  if (ms.length === 0) return null;
  return (
    <div className="mt-3 space-y-2" data-testid={`meters-${a.id}`}>
      {ms.map((m) => {
        const b = band(m.used);
        return (
          <div key={m.key} data-testid={`meter-${a.id}-${m.key}`} data-band={b}>
            <div className="flex items-center justify-between text-xs">
              <span>{m.label}{b === "danger" && <span aria-label="near limit" title="80% or more used" className="ml-2 inline-block h-2 w-2 rounded-full align-middle" style={{ background: "#EF4444" }} />}</span>
              <span className={b === "safe" ? "text-blueLight" : "text-goldLight"}>{Math.round(m.used * 100)}% used · {m.detail}</span>
            </div>
            <div className="mt-1 h-1.5 rounded bg-border" role="meter" aria-label={m.label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(m.used * 100)}>
              <div className={`h-1.5 rounded ${b === "safe" ? "bg-blue" : "bg-gold"}`} style={{ width: `${Math.round(m.used * 100)}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
function Stat({ k, v, warn }: { k: string; v: React.ReactNode; warn?: boolean }) {
  return (
    <div className={`rounded-lg border p-2 ${warn ? "border-gold" : "border-border"}`}>
      <div className="text-xs opacity-75">{k}</div>
      <div className={warn ? "text-goldLight" : ""}>{v}</div>
    </div>
  );
}

export default function Dashboard() {
  usePageTitle("Dashboard");
  const q = useQuery({ queryKey: ["dashboard"], queryFn: () => api<Dash>("/api/dashboard"), refetchInterval: 5000 });
  const d = q.data;
  if (!d) return <p role="status">Loading…</p>;
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-gold">Dashboard</h1>
      <Markets />
      <p className="text-sm">Session {d.session} · Automation <b className="text-gold">{d.mode}</b> · Bias:{" "}
        {Object.entries(d.bias).map(([s, b]) => <span key={s} className="mr-2">{s} <b className="text-gold">{b}</b></span>)}
      </p>
      <WhyNoTrade />
      {d.accounts.length === 0 && <p>No accounts yet — add one on the Automation page.</p>}
      <div className="grid gap-4 lg:grid-cols-2">
        {d.accounts.map((a) => {
          const nearKill = a.to_mll != null && a.kill_at != null && Number(a.to_mll) <= Number(a.kill_at) * 2;
          return (
            <section key={a.id} data-testid={`dash-${a.id}`} className="rounded-xl border border-border bg-card p-4">
              <h2 className="font-semibold text-gold">{a.label} <span className="text-sm font-normal text-blue">{a.stage} · {a.paper ? "APP PAPER" : a.stage === "LIVE" ? "LUCID LIVE $" : "LUCID SIM"} · {a.armed ? "armed" : "disarmed"}</span></h2>
              {a.paused && <p className="text-sm text-goldLight">⚠ paused: {a.paused}</p>}
              {a.idle_days != null && a.idle_alert_days != null && a.idle_days >= a.idle_alert_days && (
                <p className="text-sm text-goldLight">⚠ No trade for {a.idle_days} days — Lucid deletes accounts with no $1 P&amp;L in {a.idle_delete_days} days.</p>
              )}
              {a.error ? <p className="text-sm text-goldLight">⚠ {a.error}</p> : (
                <div className="mt-2 grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
                  <Stat k="Balance" v={money(a.balance)} />
                  <Stat k="Today" v={<Pnl v={a.today_pnl} />} />
                  <Stat k="Open" v={<Pnl v={a.open_pnl} />} />
                  <Stat k={`To MLL ${a.mll_locked ? "(locked)" : ""}`} v={`${money(a.to_mll)} (MLL ${money(a.mll)})`} warn={nearKill} />
                  <Stat k="DLL room" v={money(a.dll_left)} warn={a.dll_left != null && Number(a.dll_left) < 200} />
                  <Stat k="Trades today" v={a.trades_today} />
                  {a.consistency_cap && <Stat k="Consistency cap / stop" v={`${money(a.consistency_cap)} / ${money(a.consistency_stop)}`} warn={Number(a.today_pnl) >= Number(a.consistency_stop)} />}
                  {a.target_left != null && <Stat k="Eval target left" v={money(a.target_left)} />}
                  <Stat k={`Profit from ≤${a.fast_hold_s}s trades (Lucid max ${a.fast_limit_pct}%)`} v={`${Number(a.fast_profit_pct ?? 0).toFixed(1)}%`} warn={Number(a.fast_profit_pct) >= Number(a.fast_warn_pct)} />
                </div>
              )}
              {!a.error && <Meters a={a} />}
            </section>
          );
        })}
      </div>
    </div>
  );
}
