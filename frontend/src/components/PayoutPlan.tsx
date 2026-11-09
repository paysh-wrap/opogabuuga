import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { etDateTime } from "../lib/time";

interface Settings {
  skim_mode: "half" | "off"; frequency: "weekly" | "on_demand" | "every_n_sessions"; check_time: string; sweep_above: string; buffer: string;
  mode?: "sweep_skim" | "max_eligible"; min_sessions_between?: number; session_check_time?: string; min_pct_of_cap?: string | null;
}
type SaveBody = Pick<Settings, "skim_mode" | "frequency"> & { mode?: Settings["mode"]; min_sessions_between?: number; min_pct_of_cap?: string | null };
interface PlanResp {
  tracker: { year: number; ytd_gross: string; ytd_net: string; target_net: string; floor_net: string; target_pct: string; floor_pct: string; payouts_processed: number };
  projection: { basis: string; monthly_net: string; months: { month: string; net: string; cumulative: string }[] };
  next_payout: {
    check_at: string | null; frequency: string; skim_mode: string; total: string;
    accounts: { account_id: number; label: string; balance?: string; kind?: string | null; amount?: string; net?: string; reason?: string; error?: string }[];
  };
}
const usd = (v: string) => `$${Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const card = "rounded-xl border border-border bg-card p-4";

export function PayoutSettings() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["payout-settings"], queryFn: () => api<Settings>("/api/payouts/settings") });
  const [err, setErr] = useState("");
  const save = useMutation({
    mutationFn: (b: SaveBody) => api<Settings>("/api/payouts/settings", { method: "PUT", body: JSON.stringify(b) }),
    onMutate: () => setErr(""),
    onSuccess: () => ["payout-settings", "payout-plan"].forEach((k) => void qc.invalidateQueries({ queryKey: [k] })),
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Save failed"),
  });
  const s = q.data;
  return (
    <section className={card} data-testid="payout-settings">
      <h2 className="font-semibold text-gold">Payout settings</h2>
      {q.isLoading && <p role="status" className="text-sm">Loading…</p>}
      {q.error && <p role="alert" className="text-sm text-goldLight">⚠ Cannot load payout settings.</p>}
      {err && <p role="alert" className="text-sm text-goldLight">⚠ {err}</p>}
      {s && (
        <div className="mt-2 flex flex-wrap items-end gap-4 text-sm">
          <label className="flex min-w-0 max-w-full flex-col">Mode
            <select aria-label="Payout mode" value={s.mode === "max_eligible" ? "max" : s.skim_mode} disabled={save.isPending}
              onChange={(e) => {
                const v = e.target.value;
                save.mutate(v === "max"
                  ? { skim_mode: s.skim_mode, frequency: s.frequency, mode: "max_eligible", min_pct_of_cap: s.min_pct_of_cap ?? null }
                  : { skim_mode: v as Settings["skim_mode"], frequency: s.frequency, mode: "sweep_skim", min_pct_of_cap: s.min_pct_of_cap ?? null });
              }}>
              <option value="max">Largest allowed (Lucid Pro: balance − buffer, capped)</option>
              <option value="half">Sweep + skim (half of week profit once MLL is locked)</option>
              <option value="off">Sweep only</option>
            </select></label>
          <label className="flex min-w-0 max-w-full flex-col">Frequency
            <select aria-label="Payout frequency" value={s.frequency} disabled={save.isPending}
              onChange={(e) => save.mutate({ skim_mode: s.skim_mode, frequency: e.target.value as Settings["frequency"], min_pct_of_cap: s.min_pct_of_cap ?? null })}>
              <option value="every_n_sessions">Every {s.min_sessions_between ?? 2}–3 days when eligible ({s.session_check_time ?? "17:05"} ET)</option>
              <option value="weekly">Weekly ({s.check_time} ET)</option>
              <option value="on_demand">On demand (Check now only)</option>
            </select></label>
          {s.mode === "max_eligible" && (
            <label className="flex min-w-0 max-w-full flex-col">Size
              <select aria-label="Payout size" value={s.min_pct_of_cap ? "half" : "any"} disabled={save.isPending}
                onChange={(e) => save.mutate({ skim_mode: s.skim_mode, frequency: s.frequency, min_pct_of_cap: e.target.value === "half" ? "0.5" : null })}>
                <option value="any">As soon as eligible</option>
                <option value="half">Wait for ≥ 50% of the cap (most take-home on 100K/150K)</option>
              </select></label>
          )}
          <p className="text-xs">{s.mode === "max_eligible" ? "Largest payout Lucid allows" : `Sweep down to ${usd(s.sweep_above)}`}; never below the {usd(s.buffer)} buffer; 40% consistency per cycle. Lucid has no API — the app tells you when to request in your Lucid dashboard. Changes are audited.</p>
        </div>
      )}
    </section>
  );
}

export function PlanTracker() {
  const q = useQuery({ queryKey: ["payout-plan"], queryFn: () => api<PlanResp>("/api/plan"), refetchInterval: 60_000 });
  if (q.isLoading) return <section className={card}><p role="status">Loading plan…</p></section>;
  if (q.error || !q.data?.tracker) return <section className={card}><p role="alert" className="text-goldLight">⚠ Cannot load the plan.</p></section>;
  const { tracker: t, projection: p, next_payout: n } = q.data;
  return (
    <>
      <section className={card} data-testid="next-payout">
        <h2 className="font-semibold text-gold">Next payout estimate</h2>
        <p className="mt-1 text-sm">{n.check_at ? `Next check ${etDateTime(n.check_at)}` : "On demand — use Check now"} · estimated total <b className="text-gold">{usd(n.total)}</b></p>
        {n.accounts.length === 0 && <p className="text-sm">No FUNDED accounts.</p>}
        <ul className="mt-2 space-y-1 text-sm">
          {n.accounts.map((a) => (
            <li key={a.account_id} data-testid={`next-${a.account_id}`}>
              <b className="text-gold">{a.label || a.account_id}</b>{" "}
              {a.error ? <span className="text-goldLight">⚠ {a.error}</span>
                : a.kind ? <>{a.kind} {usd(a.amount!)} (net {usd(a.net!)}) · balance {usd(a.balance!)}</>
                  : <>none yet — {a.reason?.replace(/_/g, " ").toLowerCase()} · balance {usd(a.balance!)}</>}
            </li>
          ))}
        </ul>
      </section>
      <section className={card} data-testid="plan-tracker">
        <h2 className="font-semibold text-gold">{t.year} plan tracker</h2>
        <p className="mt-1 text-sm">Net paid this year <b className="text-gold">{usd(t.ytd_net)}</b> ({t.payouts_processed} payouts processed) ·
          {" "}{t.floor_pct}% of the {usd(t.floor_net)} floor · {t.target_pct}% of the {usd(t.target_net)} target</p>
        <div className="mt-2 h-2 rounded bg-border" aria-hidden><div className="h-2 rounded bg-gold" style={{ width: `${Math.min(100, Number(t.target_pct))}%` }} /></div>
      </section>
      <section className={card} data-testid="projection">
        <h2 className="font-semibold text-gold">12-month projection</h2>
        <p className="mt-1 text-xs">Basis: {p.basis} → {usd(p.monthly_net)} per month. Not a promise; it moves with real payouts.</p>
        <table className="mt-2 w-full text-sm"><tbody>
          {p.months.map((m) => (
            <tr key={m.month} className="border-t border-border"><td className="py-0.5">{m.month}</td><td>{usd(m.net)}</td><td className="text-gold">{usd(m.cumulative)}</td></tr>
          ))}
        </tbody></table>
      </section>
    </>
  );
}
