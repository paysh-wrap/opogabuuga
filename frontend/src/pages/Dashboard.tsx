import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { usePageTitle } from "../components/usePageTitle";
import Markets from "../components/Markets";
import MarketPanel from "../components/MarketPanel";
import WhyNoTrade from "../components/WhyNoTrade";
import IncomeProjection from "../components/IncomeProjection";
import HindsightNote from "../components/HindsightNote";
import RuleMeters from "../components/RuleMeters";
import { PayoutConsistencyNote, type PayoutConsistencyView } from "../components/PayoutConsistency";
import MissionBento from "../components/MissionBento";
import { CushionChip, type CushionView } from "../components/TrailCushionCard";
import MandatoryChecklist from "../components/MandatoryChecklist";
import { ApprovalQueue, BiasAndBlackouts, CooldownBanner, EvalPaceCard, PlanProgress } from "../components/DashboardExtras";

const chip = "rounded border px-1.5 text-[11px] font-semibold";

interface Acct {
  id: number; label: string; stage: string; paper: boolean; armed: boolean; paused: string | null; error?: string;
  balance?: string; open_pnl?: string; mll?: string | null; to_mll?: string | null; kill_at?: string; today_pnl?: string;
  trades_today?: number; dll_left?: string | null; consistency_cap?: string | null; consistency_stop?: string | null;
  target_left?: string | null; mll_locked?: boolean; fast_profit_pct?: string; fast_warn_pct?: string; fast_limit_pct?: string; fast_hold_s?: number; idle_days?: number; idle_alert_days?: number; idle_delete_days?: number;
  max_loss?: string; dll_limit?: string | null; payout_consistency?: PayoutConsistencyView | null;
  guard_on?: boolean; eval_mode_on?: boolean; day_lockin?: boolean; day_net_r?: string; day_lockin_r?: string;
  cushion?: CushionView | null;
}
interface Dash { session: string; mode: string; bias: Record<string, string>; accounts: Acct[] }

const money = (v?: string | null) => (v == null ? "—" : `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })}`);
function Pnl({ v }: { v?: string }) {
  const n = Number(v ?? 0);
  return <span className="font-semibold text-gold">{n > 0 ? "▲ +" : n < 0 ? "▼ −" : ""}{money(String(Math.abs(n)))}</span>;
}
function Stat({ k, v, warn }: { k: string; v: React.ReactNode; warn?: boolean }) {
  return (
    <div className={`stat-tile ${warn ? "stat-warn" : ""}`}>
      <div className="text-[11px] uppercase tracking-wider opacity-70">{k}</div>
      <div className={`mt-0.5 text-base tabular-nums ${warn ? "text-goldLight" : ""}`}>{v}</div>
    </div>
  );
}

export default function Dashboard() {
  usePageTitle("Dashboard");
  const q = useQuery({ queryKey: ["dashboard"], queryFn: () => api<Dash>("/api/dashboard"), refetchInterval: 5000 });
  const d = q.data;
  if (q.error) return <p role="alert">Cannot load the dashboard: {q.error instanceof Error ? q.error.message : "unknown error"}</p>;
  if (!d) return <p role="status">Loading…</p>;
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-gold">Dashboard</h1>
      <MissionBento accounts={d.accounts} mode={d.mode} />
      <MandatoryChecklist />
      <Markets />
      <MarketPanel />
      <p className="text-sm">Session {d.session} · Automation <b className="text-gold">{d.mode}</b> · Bias:{" "}
        {Object.entries(d.bias).map(([s, b]) => <span key={s} className="mr-2">{s} <b className="text-gold">{b}</b></span>)}
      </p>
      <CooldownBanner />
      <div className="grid gap-4 lg:grid-cols-3">
        <PlanProgress />
        <ApprovalQueue />
        <BiasAndBlackouts />
      </div>
      <HindsightNote />
      <IncomeProjection />
      <WhyNoTrade />
      {d.accounts.length === 0 && <p>No accounts yet — add one on the Automation page.</p>}
      <div className="grid gap-4 lg:grid-cols-2">
        {d.accounts.map((a) => {
          const nearKill = a.to_mll != null && a.kill_at != null && Number(a.to_mll) <= Number(a.kill_at) * 2;
          return (
            <section key={a.id} data-testid={`dash-${a.id}`} className="rounded-xl border border-border bg-card p-4">
              <h2 className="font-semibold text-gold">{a.label} <span className="text-sm font-normal text-blue">{a.stage} · {a.paper ? "APP PAPER" : a.stage === "LIVE" ? "LUCID LIVE $" : "LUCID SIM"} · {a.armed ? "armed" : "disarmed"}</span></h2>
              <div className="mt-1 flex flex-wrap gap-1" data-testid={`badges-${a.id}`}>
                {a.mll_locked && <span className={`${chip} border-gold text-gold`}>MLL LOCKED</span>}
                {a.guard_on !== undefined && <span className={`${chip} border-border text-blueLight`}>GUARD {a.guard_on ? "ON" : "OFF"}</span>}
                {a.eval_mode_on && <span className={`${chip} border-gold text-gold`}>EVAL MODE</span>}
                <CushionChip c={a.cushion} />
                {a.day_lockin && <span className={`${chip} border-gold text-goldLight`} title={`Today ${a.day_net_r}R ≥ ${a.day_lockin_r}R: next trade at floor %`}>DAY LOCK-IN</span>}
              </div>
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
                  {a.idle_days != null && <Stat k="Days since last trade" v={a.idle_days} warn={a.idle_alert_days != null && a.idle_days >= a.idle_alert_days} />}
                  {a.consistency_cap && <Stat k="Consistency cap / stop" v={`${money(a.consistency_cap)} / ${money(a.consistency_stop)}`} warn={Number(a.today_pnl) >= Number(a.consistency_stop)} />}
                  {a.target_left != null && <Stat k="Eval target left" v={money(a.target_left)} />}
                  <Stat k={`Profit from ≤${a.fast_hold_s}s trades (Lucid max ${a.fast_limit_pct}%)`} v={`${Number(a.fast_profit_pct ?? 0).toFixed(1)}%`} warn={Number(a.fast_profit_pct) >= Number(a.fast_warn_pct)} />
                </div>
              )}
              {!a.error && a.payout_consistency && <div className="mt-2"><PayoutConsistencyNote v={a.payout_consistency} id={a.id} /></div>}
              {!a.error && <RuleMeters a={a} />}
              {a.stage === "EVAL" && <EvalPaceCard id={a.id} />}
            </section>
          );
        })}
      </div>
    </div>
  );
}
