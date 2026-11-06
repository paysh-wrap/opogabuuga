import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";

interface Acct { id: number; label: string; stage: string }
interface Market { symbol: string; name: string; enabled: boolean }
interface Result {
  signal_id: number;
  plan: { entry: string; stop: string; take_profit: string; rr: string };
  result: { ok: boolean; reason: string | null; contracts?: number };
}
const btn = "rounded-md border px-3 py-1.5 text-sm font-semibold disabled:opacity-50";

/** Manual order ticket (§18 Trade). The server runs the same risk/guard/hedge/consistency checks and PAPER/LIVE
 *  gating as automated orders; size comes from the risk engine, never from this form. */
export default function ManualTicket({ accounts }: { accounts: Acct[] }) {
  const qc = useQueryClient();
  const markets = useQuery({ queryKey: ["markets"], queryFn: () => api<{ markets: Market[] }>("/api/markets") });
  const enabled = markets.data?.markets?.filter((m) => m.enabled) ?? [];
  const [f, setF] = useState({ account_id: "", symbol: "", direction: "LONG", stop: "", take_profit: "" });
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const symbol = f.symbol || enabled[0]?.symbol || "";
  const account = f.account_id || (accounts[0] ? String(accounts[0].id) : "");
  const send = useMutation({
    mutationFn: () => api<Result>("/api/orders/manual", { method: "POST", body: JSON.stringify({
      account_id: Number(account), symbol, direction: f.direction, stop: f.stop, take_profit: f.take_profit }) }),
    onMutate: () => setMsg(null),
    onSuccess: (r) => {
      setMsg(r.result.ok
        ? { ok: true, text: `Placed ${r.result.contracts} contract(s): entry ${r.plan.entry}, stop ${r.plan.stop}, target ${r.plan.take_profit} (${Number(r.plan.rr).toFixed(2)}R).` }
        : { ok: false, text: `Refused by risk checks: ${r.result.reason}` });
      ["positions", "automation", "accounts"].forEach((k) => void qc.invalidateQueries({ queryKey: [k] }));
    },
    onError: (e) => setMsg({ ok: false, text: e instanceof ApiError ? e.message : "Request failed" }),
  });
  const valid = account && symbol && Number(f.stop) > 0 && Number(f.take_profit) > 0;
  const inp = "w-28";
  return (
    <section className="rounded-xl border border-border bg-card p-4" data-testid="manual-ticket">
      <h2 className="font-semibold text-gold">Manual ticket</h2>
      <p className="mt-1 text-xs">Market entry at the current price. Size, R:R limits, hedge lock, consistency, DLL and every other check are
        applied by the server exactly as for automated orders. Recorded as MANUAL.</p>
      {accounts.length === 0 ? <p className="mt-2 text-sm">No accounts yet.</p> : (
        <form className="mt-2 flex flex-wrap items-end gap-3 text-sm" onSubmit={(e) => { e.preventDefault(); send.mutate(); }}>
          <label className="flex flex-col">Account
            <select aria-label="Ticket account" value={account} onChange={(e) => setF({ ...f, account_id: e.target.value })}>
              {accounts.map((a) => <option key={a.id} value={a.id}>{a.label || a.id} ({a.stage})</option>)}
            </select></label>
          <label className="flex flex-col">Market
            <select aria-label="Ticket market" value={symbol} onChange={(e) => setF({ ...f, symbol: e.target.value })}>
              {enabled.map((m) => <option key={m.symbol} value={m.symbol}>{m.name} ({m.symbol})</option>)}
            </select></label>
          <label className="flex flex-col">Side
            <select aria-label="Ticket side" value={f.direction} onChange={(e) => setF({ ...f, direction: e.target.value })}>
              <option value="LONG">▲ LONG</option><option value="SHORT">▼ SHORT</option>
            </select></label>
          <label className="flex flex-col">Stop<input aria-label="Ticket stop" inputMode="decimal" className={inp} value={f.stop} onChange={(e) => setF({ ...f, stop: e.target.value })} /></label>
          <label className="flex flex-col">Target<input aria-label="Ticket target" inputMode="decimal" className={inp} value={f.take_profit} onChange={(e) => setF({ ...f, take_profit: e.target.value })} /></label>
          <button type="submit" data-testid="ticket-submit" disabled={!valid || send.isPending} className={`${btn} border-gold text-gold`}>
            {send.isPending ? "Checking…" : "Send order"}</button>
        </form>
      )}
      {msg && <p role={msg.ok ? "status" : "alert"} data-testid="ticket-msg" className="mt-2 text-sm text-goldLight">{msg.ok ? "✓" : "⚠"} {msg.text}</p>}
    </section>
  );
}
