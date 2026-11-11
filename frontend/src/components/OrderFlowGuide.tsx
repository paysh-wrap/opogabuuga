import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, type ConnectionsResponse, type WebhookStatus } from "../lib/api";
import { publicBaseOf, type TaAdvisor } from "../lib/orderflow";

const card = "rounded-xl border border-border bg-card p-4 text-sm";

/** D109 B: step-by-step "add the Paytience Order Flow indicator to TradingView". The webhook URL comes from the same
 *  sources as the Connections page; the secret is never printed here (it is revealed only on the Connections page). */
export function OrderFlowGuide() {
  const conns = useQuery({ queryKey: ["connections"], queryFn: () => api<ConnectionsResponse>("/api/connections"), refetchInterval: 60_000 });
  const st = useQuery({ queryKey: ["webhook-status"], queryFn: () => api<WebhookStatus>("/api/webhook/status"), refetchInterval: 60_000 });
  const base = publicBaseOf(conns.data?.connections ?? []);
  const url = base ? `${base.replace(/\/$/, "")}${st.data?.path ?? "/api/webhook/tradingview"}` : undefined;
  const [copied, setCopied] = useState(false);
  return (
    <section className={card} data-testid="of-guide">
      <h2 className="font-semibold text-gold">Add the Paytience Order Flow indicator to TradingView</h2>
      <ol className="mt-2 list-decimal space-y-1 pl-5">
        <li>Download <a href="/api/pine/orderflow" download data-testid="of-download" className="text-gold underline">Paytience_OrderFlow.pine</a> (pine/Paytience_OrderFlow.pine) and open it in a text editor.</li>
        <li>In TradingView open a <b className="text-gold">MNQ1!</b> or <b className="text-gold">MGC1!</b> chart on the <b className="text-gold">1-minute</b> timeframe.</li>
        <li>Open the <b className="text-gold">Pine Editor</b> (bottom panel), delete the template, paste the whole script, click <b className="text-gold">Save</b>, then <b className="text-gold">Add to chart</b>.</li>
        <li>Data: real footprint delta (<code>request.footprint</code>) needs a TradingView <b className="text-gold">Premium or Ultimate</b> plan; otherwise the script uses <b className="text-gold">estimated</b> delta and every alert says <code>delta_source=est</code>. You also need <b className="text-gold">CME real-time data</b> (MNQ: CME, MGC: COMEX) — delayed data gives late alerts.</li>
        <li>Indicator settings → <b className="text-gold">Webhook secret</b>: paste the secret from the <a href="/connections" className="text-gold underline">Connections page</a> (Reveal there; never share it).</li>
        <li>Create the alert (clock icon → Create alert): Condition = <b className="text-gold">Paytience Order Flow</b> → <b className="text-gold">Any alert() function call</b>.</li>
        <li>Notifications → <b className="text-gold">Webhook URL</b> = the URL below. Message = <code>{"{{alert message}}"}</code> (TradingView usually fills this for alert() calls — leave it as is).</li>
        <li>Expiration: pick <b className="text-gold">Open-ended</b> if your plan offers it; otherwise note the expiry date and re-create the alert before it runs out (an expired alert sends nothing).</li>
        <li>One alert <b className="text-gold">per symbol</b>: repeat steps 2–8 for the other market (MNQ1! and MGC1! each need their own chart + alert). Keep the Paytience_Bridge heartbeat alerts on too.</li>
      </ol>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="w-28 shrink-0 text-blue">Webhook URL</span>
        {url ? (
          <>
            <code data-testid="of-webhook-url" className="break-all text-goldLight">{url}</code>
            <button className="rounded border border-blue px-2 py-0.5 text-xs text-blue" onClick={() => { void navigator.clipboard?.writeText(url); setCopied(true); setTimeout(() => setCopied(false), 1500); }}>{copied ? "Copied" : "Copy"}</button>
          </>
        ) : (
          <span data-testid="of-webhook-url" className="text-goldLight">{conns.isLoading ? "Loading…" : "No public URL yet — start the tunnel on the Connections page"}</span>
        )}
      </div>
      <p className="mt-1 text-xs text-blue">Webhook secret: {st.data ? (st.data.secret_set ? "set (shown only on the Connections page)" : "not set yet — set it on the Connections page") : "…"}</p>
    </section>
  );
}

/** D109 A: TradingAgents advisor toggle + today's advice (ADVISORY — never blocks unless the plan flag + proven ledger). */
export function TaAdvisorPanel({ a, symbol }: { a: TaAdvisor; symbol: string }) {
  const qc = useQueryClient();
  const [err, setErr] = useState("");
  const toggle = useMutation({
    mutationFn: () => api("/api/risk/settings", { method: "PUT", body: JSON.stringify({ changes: { [a.setting]: !a.enabled }, note: `Order Flow: TradingAgents advisor ${a.enabled ? "off" : "on"}` }) }),
    onSuccess: () => { setErr(""); void qc.invalidateQueries({ queryKey: ["orderflow"] }); },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Request failed"),
  });
  const adv = a.advice;
  return (
    <section className={card} data-testid="of-ta-advisor">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="font-semibold text-gold">TradingAgents advisor</h2>
        <span className="rounded border border-gold px-2 py-0.5 text-xs text-gold">advisory</span>
        <button className="rounded border border-blue px-2 py-0.5 text-xs text-blue" onClick={() => toggle.mutate()} disabled={toggle.isPending} data-testid="of-ta-toggle">
          {a.enabled ? "ON — turn off" : "OFF — turn on"}
        </button>
      </div>
      <p className="mt-1 text-xs text-blue">Runs the daily TradingAgents bias at {a.at} ET (1 h before the first Order Flow entry window). An opposite-side alert is {a.blocks ? "skipped (OF_TA_DISAGREES) once the AI ledger is proven, else annotated" : "annotated with a warning only"}. No advice (no key / failure) never blocks trading.</p>
      {a.enabled && (
        <p className="mt-1" data-testid="of-ta-advice">
          {adv && adv.side ? (
            <>{symbol} {a.session}: <b className="text-gold">{adv.side === "LONG" ? "▲ LONG" : adv.side === "SHORT" ? "▼ SHORT" : "NEUTRAL"}</b>{adv.confidence != null && ` · confidence ${adv.confidence}%`} · {new Date(adv.at).toLocaleTimeString()} · advisory</>
          ) : adv ? <>{symbol} {a.session}: no advice today ({adv.raw ?? "no result"}) — trading unaffected</> : <>{symbol} {a.session}: not run yet (due {a.at} ET)</>}
        </p>
      )}
      {err && <p role="alert" className="mt-1 text-xs text-goldLight">{err}</p>}
    </section>
  );
}
