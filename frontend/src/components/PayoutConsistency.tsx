import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

/** D89: Lucid's payout-eligibility consistency (LucidPro FUNDED). Shape of `payout_consistency` from the API. */
export interface PayoutConsistencyView {
  pct: string | null; limit: string; largest_day: string; cycle_profit: string; eligible: boolean;
  needed_cycle_profit: string; still_needed: string; text: string; date_known: boolean; verify: string | null;
}

/** Gold VERIFY badge while the purchase / reset date is unknown (the stricter limit is used until it is entered). */
export function PayoutConsistencyNote({ v, id }: { v: PayoutConsistencyView; id: number | string }) {
  return (
    <div data-testid={`pcons-${id}`} className="text-sm">
      <p>
        <span className={`mr-2 rounded border px-1.5 text-[11px] font-semibold ${v.eligible ? "border-blue text-blueLight" : "border-gold text-gold"}`}>
          {v.eligible ? "✔ PAYOUT CONSISTENCY MET" : "PAYOUT CONSISTENCY NOT MET"}
        </span>
        {v.pct != null ? `largest day ${Number(v.pct).toFixed(1)}% of cycle profit` : "no cycle profit yet"} · limit {Number(v.limit)}%
        {!v.date_known && <span className="ml-2 rounded border border-gold px-1.5 text-[11px] font-semibold text-gold" title={v.verify ?? ""}>VERIFY</span>}
      </p>
      <p className="mt-0.5 text-xs">{v.text}</p>
      {v.verify && <p className="mt-0.5 text-xs text-goldLight">{v.verify}</p>}
    </div>
  );
}

/** Payouts page card: every FUNDED Pro account, what is still needed before a payout can be requested. */
export function PayoutConsistencyCard() {
  const q = useQuery({
    queryKey: ["payout-consistency"],
    queryFn: () => api<{ accounts: ({ account_id: number; label: string } & PayoutConsistencyView)[] }>("/api/payouts/consistency"),
    refetchInterval: 30_000,
  });
  if (q.isLoading || q.error || !q.data?.accounts?.length) return null;
  return (
    <section className="rounded-xl border border-border bg-card p-4" data-testid="payout-consistency">
      <h2 className="font-semibold text-gold">Payout consistency (Lucid)</h2>
      <p className="mt-1 text-xs">
        To request a payout, your largest single day must be at most the limit of your profit since the last payout.
        It is a payout condition, not a breach, and it starts again after every payout. Not applied on Live.
      </p>
      <ul className="mt-2 space-y-2">
        {q.data.accounts.map((a) => (
          <li key={a.account_id}><b className="text-gold">{a.label}</b><PayoutConsistencyNote v={a} id={a.account_id} /></li>
        ))}
      </ul>
    </section>
  );
}
