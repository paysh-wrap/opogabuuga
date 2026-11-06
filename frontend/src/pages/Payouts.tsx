import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { usePageTitle } from "../components/usePageTitle";
import PnlCalendar from "../components/PnlCalendar";
import { PayoutSettings, PlanTracker } from "../components/PayoutPlan";

interface P { id: number; label: string; week: string; kind: string; amount: string; balance_before: string; status: string }
const btn = "rounded-md border px-3 py-1 text-sm font-semibold disabled:opacity-50";

export default function Payouts() {
  usePageTitle("Payouts");
  const qc = useQueryClient();
  const [err, setErr] = useState("");
  const q = useQuery({ queryKey: ["payouts"], queryFn: () => api<{ payouts: P[] }>("/api/payouts"), refetchInterval: 15000 });
  const run = useMutation({
    mutationFn: (f: () => Promise<unknown>) => f(),
    onMutate: () => setErr(""),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["payouts"] }),
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Request failed"),
  });
  const set = (id: number, status: string) =>
    run.mutate(() => api(`/api/payouts/${id}/status`, { method: "POST", body: JSON.stringify({ status }) }));
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-gold">Payouts</h1>
      <p className="text-sm">Weekly check Fri 17:05 ET. Lucid has no API: request the amount in your Lucid dashboard, then mark it here.
        While a payout is <b>submitted</b>, that account doesn't trade. The balance never goes below the $26,100 buffer.</p>
      {err && <p role="alert" className="rounded-lg border border-gold p-3 text-sm text-goldLight">⚠ {err}</p>}
      <button className={`${btn} border-blue text-blue`} onClick={() => run.mutate(() => api("/api/payouts/check", { method: "POST" }))}>Check now</button>
      <section className="rounded-xl border border-border bg-card p-4">
        {q.data?.payouts.length === 0 && <p className="text-sm">No payouts yet.</p>}
        <table className="w-full text-sm"><tbody>
          {q.data?.payouts.map((p) => (
            <tr key={p.id} data-testid={`payout-${p.id}`} className="border-t border-border">
              <td className="py-1">{p.week}</td><td className="text-gold">{p.label}</td><td>{p.kind}</td>
              <td className="font-semibold text-gold">${Number(p.amount).toFixed(2)}</td><td>{p.status}</td>
              <td className="space-x-2 text-right">
                {p.status === "ready" && <button className={`${btn} border-gold text-gold`} onClick={() => set(p.id, "submitted")}>I requested it</button>}
                {p.status === "submitted" && <button className={`${btn} border-gold text-gold`} onClick={() => set(p.id, "processed")}>Paid</button>}
                {(p.status === "ready" || p.status === "submitted") && <button className={`${btn} border-border text-blue`} onClick={() => set(p.id, "cancelled")}>Cancel</button>}
              </td>
            </tr>
          ))}
        </tbody></table>
      </section>
      <PayoutSettings />
      <PlanTracker />
      <PnlCalendar />
    </div>
  );
}
