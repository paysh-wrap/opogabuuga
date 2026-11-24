import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

const btn = "rounded-md border px-3 py-1 text-sm font-semibold disabled:opacity-50";

interface OD { account_id: number; label: string; available: boolean; amount: string; net: string; limited_by: string; reason: string; message: string; dll_enabled: boolean; hedging_violation: boolean; paused: boolean }

// D182: On-demand payouts (CONFIRMED, Lucid help center, user screenshots 2026-11-24). The app only plans; the user requests in Lucid.
export default function OnDemandCard({ run }: { run: (f: () => Promise<unknown>) => void }) {
  const q = useQuery({ queryKey: ["payouts-on-demand"], queryFn: () => api<{ status: string; pause_rule: string; accounts: OD[] }>("/api/payouts/on-demand"), refetchInterval: 15000 });
  const by = (s: string) => (s === "session_profit" ? "this session's profit" : s === "cap" ? "the plan's payout cap" : "the balance above the buffer");
  return (
    <section className="rounded-xl border border-border bg-card p-4" data-testid="on-demand">
      <h2 className="font-semibold text-gold">On-demand payouts <span className="text-xs text-blue">({q.data?.status ?? "CONFIRMED (Lucid help center)"})</span></h2>
      <p className="mt-1 text-xs" data-testid="on-demand-rule">LucidPro with the Daily Loss Limit ON: request during the session (6:00 PM to 3:45 PM ET) from the profit made that session. {q.data?.pause_rule} A Hedging Violation makes the account ineligible. The app never submits a payout: plan it here, request it in your Lucid dashboard, then press "I requested it" below.</p>
      {q.data?.accounts?.length === 0 && <p className="mt-2 text-sm">No funded accounts.</p>}
      <ul className="mt-2 space-y-2 text-sm">
        {q.data?.accounts?.map((a) => (
          <li key={a.account_id} data-testid={`od-${a.account_id}`} className="flex flex-wrap items-center gap-2">
            <b className="text-gold">{a.label}</b>
            {a.available ? (
              <span data-testid={`od-amount-${a.account_id}`}>On-demand available: <b className="text-gold">${Number(a.amount).toLocaleString()}</b> gross (net ${Number(a.net).toLocaleString()}), limited by {by(a.limited_by)}. Minimum $500; consistency and buffer already checked.</span>
            ) : <span data-testid={`od-reason-${a.account_id}`} className="text-blue">Not available: {a.message}</span>}
            {a.paused && <span className="rounded border border-gold px-1 text-xs text-gold">TRADING PAUSED until the end of the trading day</span>}
            <label className="ml-auto text-xs"><input type="checkbox" checked={a.hedging_violation} onChange={(e) => run(() => api(`/api/accounts/${a.account_id}`, { method: "PATCH", body: JSON.stringify({ hedging_violation: e.target.checked }) }))} /> Hedging Violation flagged by Lucid</label>
            <button className={`${btn} border-gold text-gold`} disabled={!a.available} onClick={() => run(() => api(`/api/payouts/on-demand/${a.account_id}/plan`, { method: "POST" }))}>Plan this payout</button>
          </li>
        ))}
      </ul>
    </section>
  );
}

