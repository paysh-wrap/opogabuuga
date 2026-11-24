import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

// D59: projected weekly income from FUNDED accounts — the MAIN strategy's 5-year research results replayed through the
// chosen plan's own funded payout rules (server: app/backtest/income_projection.py). A projection, not live data.
type Fig = { net: string; gross: string };
export type Totals = Record<"per_account" | "funded" | "live" | "household", Record<"week" | "year_mean" | "year_median" | "year_p25" | "year_p75", Fig>>;
export interface IncomeResp {
  plan: string; plans: string[]; current_plan: string; basis: string; grow?: number;
  auto?: { contracts: number; candace?: number; stop_usd?: number; noise_brake?: [number, number][]; candace_brake?: [number, number][]; grow?: [number, number] | null; setup?: string } | null;
  status?: string; caveat?: string; on_demand_note?: string; max_micros?: number;
  accounts: number; funded?: number; live?: number; default_cadence?: number; cadence_labels?: Record<string, string>; live_status?: string; live_basis?: string;
  totals?: Totals; on_demand_status?: string; lost_trades_year_account?: string; pause_days_year_account?: string;
  micros: number; cadence_sessions: number; starts: number; horizon_sessions: number;
  year_mean: string; year_median: string; year_p25: string; year_p75: string; week_mean: string; per_paycheck_mean: string;
  any_payout_pct: string; bust_pct: string; max_payouts_pct: string; median_sessions_to_first: number | null; max_possible_year: string;
  paid_week_mean_account?: string; paid_year_mean_account?: string; paid_year_median_account?: string; paid_year_p25_account?: string; paid_year_p75_account?: string;
  per_payout_account?: string; cap_first_net?: string; cap_next_net?: string; payout_events_max?: number; max_possible_account?: string; max_possible_formula?: string;
  incl_unpaid_year_mean?: string; incl_unpaid_week_mean?: string; incl_unpaid_year_median?: string; weeks_in_horizon?: number;
}

const KEY = "paytience.income.calc.v3";
const MAX_MICROS = 9; // selectable 1..9 (the data file carries exactly these; the server rejects more)
const CADENCES = [5, 10, 1, 0]; // weekly, every 2 weeks, every session at the close, on-demand (CONFIRMED, Lucid help center)
type Saved = { plan: string | null; funded: number; live: number; micros: number; cadence: number | null; profile: "" | "regular" | "high"; grow: number };
const DEFAULTS: Saved = { plan: null, funded: 5, live: 0, micros: 0, cadence: null, profile: "", grow: 0 }; // cadence null = the server's default (the study's best)
// Old saved states (v1/v2: one "accounts" 1-5 = funded accounts) must still load: every field is validated, bad ones fall back.
export function loadSaved(raw: string | null): Saved {
  try {
    const o = JSON.parse(raw ?? "{}") as Partial<Saved> & { accounts?: number };
    const int = (v: unknown, lo: number, hi: number, d: number) => (typeof v === "number" && Number.isInteger(v) && v >= lo && v <= hi ? v : d);
    const funded = int(o.funded ?? o.accounts, 0, 5, 5), live = int(o.live, 0, 5, 0);
    return {
      plan: typeof o.plan === "string" ? o.plan : null, funded: funded + live < 1 ? 5 : funded, live, micros: int(o.micros, 0, MAX_MICROS, 0),
      cadence: CADENCES.includes(o.cadence as number) ? (o.cadence as number) : null,
      profile: o.profile === "regular" || o.profile === "high" ? o.profile : "", grow: [0, 500, 1000, 1500, 2000, 3000].includes(o.grow as number) ? (o.grow as number) : 0,
    };
  } catch { return DEFAULTS; }
}
const readSaved = (): Saved => { try { return loadSaved(localStorage.getItem(KEY) ?? localStorage.getItem("paytience.income.calc.v2") ?? localStorage.getItem("paytience.income.calc")); } catch { return DEFAULTS; } };

const card = "rounded-xl border border-border bg-card p-4";
const usd = (v?: string | null) => (v == null ? "—" : `$${Math.round(Number(v)).toLocaleString()}`);
const label = (p: string) => p.replace("lucid_", "Lucid ").replace(/_(\d+k)$/, " $1").replace("pro", "Pro").replace("flex", "Flex").replace("daily", "Daily").toUpperCase().replace("LUCID", "Lucid");

export default function IncomeProjection() {
  const init = useState(readSaved)[0];
  const [plan, setPlan] = useState<string | null>(init.plan);
  const [funded, setFunded] = useState(init.funded); // household: up to 5 funded + 5 live (Lucid help center, CONFIRMED)
  const [live, setLive] = useState(init.live);
  const [micros, setMicros] = useState(init.micros); // 0 = the plan's own fast-pass size + brakes
  const [cadence, setCadence] = useState<number | null>(init.cadence);
  const [profile, setProfile] = useState<"" | "regular" | "high">(init.profile); // "" = the active profile
  const [grow, setGrow] = useState(init.grow); // +1 micro per $grow of cushion above the trailing MLL (0 = fixed size)
  useEffect(() => { try { localStorage.setItem(KEY, JSON.stringify({ plan, funded, live, micros, cadence, profile, grow })); } catch { /* storage blocked */ } }, [plan, funded, live, micros, cadence, profile, grow]);
  const qs = new URLSearchParams({ funded: String(funded), live: String(live), micros: String(micros), grow: String(grow), ...(cadence == null ? {} : { cadence: String(cadence) }), ...(plan ? { plan } : {}), ...(profile ? { profile } : {}) });
  const q = useQuery({ queryKey: ["income-projection", plan, funded, live, micros, cadence, grow, profile], queryFn: () => api<IncomeResp>(`/api/income/projection?${qs}`), staleTime: 3_600_000 });
  const d = q.data;
  const sel = "rounded-md border border-border bg-card px-2 py-1 text-sm text-blue";
  return (
    <section className={card} data-testid="income-projection">
      <h2 className="font-semibold text-gold">Projected weekly income (funded + live accounts)</h2>
      <p className="mt-1 text-xs text-goldLight" data-testid="income-warning">Research projection, UNVERIFIED, not a promise. Funded accounts are lost often (see the note below).</p>
      <div className="mt-2 flex flex-wrap gap-2 text-sm">
        <label>Plan <select aria-label="Plan" className={sel} value={plan ?? d?.plan ?? ""} onChange={(e) => setPlan(e.target.value)}>
          {(d?.plans ?? []).map((p) => <option key={p} value={p}>{label(p)}{p === d?.current_plan ? " (current)" : ""}</option>)}
        </select></label>
        <label>Funded accounts (0-5) <select aria-label="Funded accounts" className={sel} value={funded} onChange={(e) => setFunded(Number(e.target.value))}>
          {[0, 1, 2, 3, 4, 5].map((n) => <option key={n} value={n} disabled={n + live < 1}>{n}</option>)}
        </select></label>
        <label>Live accounts (0-5) <select aria-label="Live accounts" className={sel} value={live} onChange={(e) => setLive(Number(e.target.value))}>
          {[0, 1, 2, 3, 4, 5].map((n) => <option key={n} value={n} disabled={n + funded < 1}>{n}</option>)}
        </select></label>
        <label>Micros each <select aria-label="Micros" className={sel} value={micros} onChange={(e) => setMicros(Number(e.target.value))}>
          <option value={0}>Auto (plan fast-pass size)</option>
          {Array.from({ length: MAX_MICROS }, (_, i) => i + 1).map((n) => <option key={n} value={n}>{n}</option>)}
        </select></label>
        <label>Size profile <select aria-label="Size profile" className={sel} value={profile} onChange={(e) => setProfile(e.target.value as "" | "regular" | "high")}>
          <option value="">active</option><option value="regular">Regular</option><option value="high">High risk</option>
        </select></label>
        <label>Payout <select aria-label="Payout cadence" className={sel} value={cadence ?? d?.default_cadence ?? 1} onChange={(e) => setCadence(Number(e.target.value))}>
          <option value={1}>every session at the close (best in the study{d?.default_cadence === 1 ? ", default" : ""})</option><option value={5}>weekly</option><option value={10}>every 2 weeks</option>
          <option value={0}>On-demand, intraday (CONFIRMED, Lucid help center)</option>
        </select></label>
        <label>Account growth <select aria-label="Account growth" className={sel} value={grow} disabled={micros === 0} onChange={(e) => setGrow(Number(e.target.value))}>
          <option value={0}>off (fixed size)</option>
          {[500, 1000, 1500, 2000, 3000].map((g) => <option key={g} value={g}>+1 micro per ${g.toLocaleString()} cushion</option>)}
        </select></label>
      </div>
      {q.isLoading && <p role="status" className="mt-2 text-sm">Calculating…</p>}
      {q.error && <p role="alert" className="mt-2 text-sm text-goldLight">⚠ Cannot load the projection.</p>}
      {d && (
        <>
          <p className="mt-3 text-sm font-semibold text-gold" data-testid="income-scenario">Profit scenario: all {d.accounts} account{d.accounts > 1 ? "s" : ""} get paid ({d.funded ?? d.accounts} funded + {d.live ?? 0} live). Amounts are NET to you (after the 10% Lucid split); gross = net / 0.9.</p>
          {(d.live ?? 0) > 0 && <p className="mt-1 text-xs text-goldLight" data-testid="income-live-note">Live accounts: {d.live_status ?? "VERIFY"}. {d.live_basis}</p>}
          <table className="mt-1 w-full text-sm" data-testid="income-table">
            <thead><tr className="text-left text-xs text-blue"><th scope="col">Figure</th><th scope="col">Per account (net)</th><th scope="col">Funded total (net)</th><th scope="col">Live total (net)</th><th scope="col">Household {d.accounts} (net)</th><th scope="col">Household {d.accounts} (gross)</th></tr></thead>
            <tbody>
              {([
                ["Per week, average", "Average income per trading week over the first year (year total / " + (d.weeks_in_horizon ?? 50) + " weeks).", "week", "income-week"],
                ["Per payout (one payout event)", "Average size of one payout when one is requested. Each payout is capped by the plan: " + usd(d.cap_first_net) + " net first, " + usd(d.cap_next_net) + " net later, per account.", "paycheck", "income-paycheck"],
                ["First year: average", "Mean year-1 total across the simulated starts that got paid.", "year_mean", "income-year"],
                ["First year: typical (median)", "Half of the paid starts earn less, half more.", "year_median", "income-median"],
                ["Middle half: low end (25th pct)", "One quarter of paid starts earn less than this.", "year_p25", "income-p25"],
                ["Middle half: high end (75th pct)", "One quarter of paid starts earn more than this.", "year_p75", "income-p75"],
                ["Most possible", "Best case: every payout at the plan cap. " + (d.max_possible_formula ?? ""), "max", "income-max"],
              ] as [string, string, string, string][]).map(([k, tip, key, id]) => {
                const one = key === "paycheck" ? Number(d.per_payout_account) : key === "max" ? Number(d.max_possible_account) : Number(d.totals?.per_account[key as keyof Totals["per_account"]].net);
                const nF = d.funded ?? d.accounts, nL = d.live ?? 0, all = one * (nF + nL);
                return (
                  <tr key={id} title={tip}><th scope="row" className="text-left font-normal">{k} <span className="text-xs text-blue" aria-label={tip}>(?)</span></th>
                    <td className="text-gold">{usd(String(one))}</td><td className="text-gold" data-testid={`${id}-funded`}>{usd(String(one * nF))}</td><td className="text-gold" data-testid={`${id}-live`}>{usd(String(one * nL))}</td>
                    <td className="text-gold" data-testid={id}>{id === "income-week" ? "▲ " : ""}{usd(String(all))}</td><td className="text-gold" data-testid={`${id}-gross`}>{usd(String(all / 0.9))}</td></tr>
                );
              })}
            </tbody>
          </table>
          <p className="mt-1 text-xs text-blue" data-testid="income-formula">Most possible = {d.max_possible_formula}. Typical wait for the 1st payout (accounts that get paid): {d.median_sessions_to_first == null ? "—" : `${d.median_sessions_to_first} trading days`}.</p>
          <p className="mt-2 text-sm text-goldLight" data-testid="income-note">Not every account gets paid: in the simulation only {d.any_payout_pct}% of accounts receive a payout and {d.bust_pct}% bust in year 1 (all accounts take the same trades, so they win and lose together). The figures above assume all {d.accounts} account{d.accounts > 1 ? "s are" : " is"} paid. Including accounts that are never paid: average {usd(d.incl_unpaid_week_mean)} per week, {usd(d.incl_unpaid_year_mean)} first-year average, {usd(d.incl_unpaid_year_median)} median (all {d.accounts}, net).</p>
          {d.auto && (
            <p className="mt-2 text-sm" data-testid="income-auto">Auto size: <b className="text-gold">NOISE {d.auto.contracts} + CANDACE {d.auto.candace ?? d.auto.contracts} micros</b> per account
              {[...(d.auto.noise_brake ?? []).map(([c, q]) => `NOISE drops to ${q} below $${c.toLocaleString()} cushion`), ...(d.auto.candace_brake ?? []).map(([c, q]) => `CANDACE drops to ${q} below $${c.toLocaleString()} cushion`)].map((t) => <span key={t}> · {t}</span>)}
            </p>
          )}
          <p className="mt-2 text-xs text-blue">{d.basis} {d.starts} start dates. All accounts take the same trades — they pay and bust together.{cadence === 0 && d.on_demand_note ? ` On-demand (${d.on_demand_status ?? "CONFIRMED"}): ${d.on_demand_note} In the simulation this costs ${d.pause_days_year_account ?? 0} paused days and ${d.lost_trades_year_account ?? 0} lost trades per account per year.` : ""}</p>
        </>
      )}
    </section>
  );
}
