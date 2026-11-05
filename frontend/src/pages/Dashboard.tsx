import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { usePageTitle } from "../components/usePageTitle";

interface Acct {
  id: number; label: string; stage: string; paper: boolean; armed: boolean; paused: string | null; error?: string;
  balance?: string; open_pnl?: string; mll?: string | null; to_mll?: string | null; kill_at?: string; today_pnl?: string;
  trades_today?: number; dll_left?: string | null; consistency_cap?: string | null; consistency_stop?: string | null;
  target_left?: string | null; mll_locked?: boolean;
}
interface Dash { session: string; mode: string; bias: Record<string, string>; accounts: Acct[] }

const money = (v?: string | null) => (v == null ? "—" : `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })}`);
function Pnl({ v }: { v?: string }) {
  const n = Number(v ?? 0);
  return <span className="font-semibold text-gold">{n > 0 ? "▲ +" : n < 0 ? "▼ −" : ""}{money(String(Math.abs(n)))}</span>;
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
      <p className="text-sm">Session {d.session} · Automation <b className="text-gold">{d.mode}</b> · Bias:{" "}
        {Object.entries(d.bias).map(([s, b]) => <span key={s} className="mr-2">{s} <b className="text-gold">{b}</b></span>)}
      </p>
      {d.accounts.length === 0 && <p>No accounts yet — add one on the Automation page.</p>}
      <div className="grid gap-4 lg:grid-cols-2">
        {d.accounts.map((a) => {
          const nearKill = a.to_mll != null && a.kill_at != null && Number(a.to_mll) <= Number(a.kill_at) * 2;
          return (
            <section key={a.id} data-testid={`dash-${a.id}`} className="rounded-xl border border-border bg-card p-4">
              <h2 className="font-semibold text-gold">{a.label} <span className="text-sm font-normal text-blue">{a.stage} · {a.paper ? "APP PAPER" : a.stage === "LIVE" ? "LUCID LIVE $" : "LUCID SIM"} · {a.armed ? "armed" : "disarmed"}</span></h2>
              {a.paused && <p className="text-sm text-goldLight">⚠ paused: {a.paused}</p>}
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
                </div>
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
}
