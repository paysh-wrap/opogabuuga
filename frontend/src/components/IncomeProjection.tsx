import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

// D59: projected weekly income from FUNDED accounts — the MAIN strategy's 5-year research results replayed through the
// chosen plan's own funded payout rules (server: app/backtest/income_projection.py). A projection, not live data.
export interface IncomeResp {
  plan: string; plans: string[]; current_plan: string; basis: string; grow?: number;
  auto?: { contracts: number; brake_below: string | null; brake_contracts: number | null } | null;
  accounts: number; micros: number; cadence_sessions: number; starts: number; horizon_sessions: number;
  year_mean: string; year_median: string; year_p25: string; year_p75: string; week_mean: string; per_paycheck_mean: string;
  any_payout_pct: string; bust_pct: string; max_payouts_pct: string; median_sessions_to_first: number | null; max_possible_year: string;
}

const card = "rounded-xl border border-border bg-card p-4";
const usd = (v?: string | null) => (v == null ? "—" : `$${Math.round(Number(v)).toLocaleString()}`);
const label = (p: string) => p.replace("lucid_", "Lucid ").replace(/_(\d+k)$/, " $1").replace("pro", "Pro").replace("flex", "Flex").replace("daily", "Daily").toUpperCase().replace("LUCID", "Lucid");

export default function IncomeProjection() {
  const [plan, setPlan] = useState<string | null>(null);
  const [accounts, setAccounts] = useState(5);
  const [micros, setMicros] = useState(0); // 0 = automatic size for the plan (D63 size table + drawdown brake)
  const [cadence, setCadence] = useState(10);
  const [profile, setProfile] = useState<"" | "regular" | "high">(""); // D64: "" = the active profile
  const [grow, setGrow] = useState(0); // D60: +1 micro per $grow of cushion above the trailing MLL (0 = fixed size)
  const qs = new URLSearchParams({ accounts: String(accounts), micros: String(micros), cadence: String(cadence), grow: String(grow), ...(plan ? { plan } : {}), ...(profile ? { profile } : {}) });
  const q = useQuery({ queryKey: ["income-projection", plan, accounts, micros, cadence, grow, profile], queryFn: () => api<IncomeResp>(`/api/income/projection?${qs}`), staleTime: 3_600_000 });
  const d = q.data;
  const sel = "rounded-md border border-border bg-card px-2 py-1 text-sm text-blue";
  return (
    <section className={card} data-testid="income-projection">
      <h2 className="font-semibold text-gold">Projected weekly income (funded accounts)</h2>
      <div className="mt-2 flex flex-wrap gap-2 text-sm">
        <label>Plan <select aria-label="Plan" className={sel} value={plan ?? d?.plan ?? ""} onChange={(e) => setPlan(e.target.value)}>
          {(d?.plans ?? []).map((p) => <option key={p} value={p}>{label(p)}{p === d?.current_plan ? " (current)" : ""}</option>)}
        </select></label>
        <label>Accounts <select aria-label="Accounts" className={sel} value={accounts} onChange={(e) => setAccounts(Number(e.target.value))}>
          {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
        </select></label>
        <label>Micros each <select aria-label="Micros" className={sel} value={micros} onChange={(e) => setMicros(Number(e.target.value))}>
          <option value={0}>Auto (by account size)</option>
          {[1, 2, 3, 4, 5, 6].map((n) => <option key={n} value={n}>{n}</option>)}
        </select></label>
        <label>Size profile <select aria-label="Size profile" className={sel} value={profile} onChange={(e) => setProfile(e.target.value as "" | "regular" | "high")}>
          <option value="">active</option><option value="regular">Regular</option><option value="high">High risk</option>
        </select></label>
        <label>Payout <select aria-label="Payout cadence" className={sel} value={cadence} onChange={(e) => setCadence(Number(e.target.value))}>
          <option value={5}>weekly</option><option value={10}>every 2 weeks</option>
        </select></label>
        <label>Account growth <select aria-label="Account growth" className={sel} value={grow} onChange={(e) => setGrow(Number(e.target.value))}>
          <option value={0}>off (fixed size)</option>
          {[500, 1000, 1500, 2000, 3000].map((g) => <option key={g} value={g}>+1 micro per ${g.toLocaleString()} cushion</option>)}
        </select></label>
      </div>
      {q.isLoading && <p role="status" className="mt-2 text-sm">Calculating…</p>}
      {q.error && <p role="alert" className="mt-2 text-sm text-goldLight">⚠ Cannot load the projection.</p>}
      {d && (
        <>
          <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1 text-sm sm:grid-cols-3">
            <dt>Per week (average)</dt><dd className="text-lg font-semibold text-gold" data-testid="income-week">▲ {usd(d.week_mean)}</dd>
            <dt>Per {d.cadence_sessions === 5 ? "weekly" : "2-week"} payout</dt><dd className="text-gold" data-testid="income-paycheck">▲ {usd(d.per_paycheck_mean)}</dd>
            <dt>First year: average</dt><dd className="text-gold">{usd(d.year_mean)}</dd>
            <dt>First year: typical (median)</dt><dd className="text-gold" data-testid="income-median">{usd(d.year_median)}</dd>
            <dt>Middle half of outcomes</dt><dd className="text-gold">{usd(d.year_p25)} – {usd(d.year_p75)}</dd>
            <dt>Most possible (all payouts at cap)</dt><dd className="text-gold">{usd(d.max_possible_year)}</dd>
            <dt>Accounts with ≥ 1 payout</dt><dd className="text-gold">{d.any_payout_pct}%</dd>
            <dt>Funded account busts in year 1</dt><dd className="text-gold" data-testid="income-bust">{d.bust_pct}%</dd>
            <dt>Typical wait for 1st payout</dt><dd className="text-gold">{d.median_sessions_to_first == null ? "—" : `${d.median_sessions_to_first} trading days`}</dd>
          </dl>
          {d.auto && (
            <p className="mt-2 text-sm" data-testid="income-auto">Auto size: <b className="text-gold">{d.auto.contracts} micro{d.auto.contracts > 1 ? "s" : ""}</b> per account
              {d.auto.brake_below && <> · drops to <b className="text-gold">{d.auto.brake_contracts}</b> when the cushion is below {Math.round(Number(d.auto.brake_below) * 100)}% of the loss limit</>}
            </p>
          )}
          <p className="mt-2 text-xs text-blue">{d.basis} {d.starts} start dates. All accounts take the same trades — they pay and bust together.</p>
        </>
      )}
    </section>
  );
}
