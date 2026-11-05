import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, ApiError, type WebhookStatus } from "../lib/api";
import { badge } from "../lib/theme";
import { etTime } from "../lib/time";

const FEED_LABEL = { FRESH: "Fresh", STALE: "Stale", CLOSED: "Market closed", NO_DATA: "No data" } as const;

export default function TradingViewSetup({ publicBase }: { publicBase?: string }) {
  const st = useQuery({ queryKey: ["webhook-status"], queryFn: () => api<WebhookStatus>("/api/webhook/status"), refetchInterval: 15_000 });
  const [secret, setSecret] = useState<string | null>(null);
  const [copied, setCopied] = useState("");
  const [err, setErr] = useState("");
  const reveal = useMutation({
    mutationFn: () => api<{ secret: string }>("/api/webhook/secret/reveal", { method: "POST" }),
    onSuccess: (d) => setSecret(d.secret),
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Request failed"),
  });
  const feeds = st.data?.feeds ?? [];
  const accepted = st.data?.accepted ?? {};
  const rejected = st.data?.rejected ?? {};
  const url = publicBase ? `${publicBase.replace(/\/$/, "")}${st.data?.path ?? "/api/webhook/tradingview"}` : undefined;

  function copy(label: string, text: string) {
    void navigator.clipboard?.writeText(text);
    setCopied(label);
    setTimeout(() => setCopied(""), 1500);
  }

  return (
    <section data-testid="tv-setup" className="rounded-xl border border-border bg-card p-4">
      <h2 className="font-semibold text-gold">TradingView setup</h2>
      <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm">
        <li>Download <a href="/api/pine/bridge" download data-testid="download-bridge">Paytience_Bridge.pine</a> and add it to an MNQ1! chart (1-minute for TIGHT, 5-minute for STD) via Pine Editor → Add to chart.</li>
        <li>Paste the webhook secret below into the indicator's <b className="text-goldLight">Webhook secret</b> setting.</li>
        <li>Create an alert → Condition <b className="text-goldLight">Paytience_Bridge</b> → <b className="text-goldLight">Any alert() function call</b> → Webhook URL below.</li>
      </ol>

      <div className="mt-3 grid gap-2 text-sm">
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-28 shrink-0">Webhook URL</span>
          {url ? (
            <>
              <code data-testid="webhook-url" className="break-all text-goldLight">{url}</code>
              <button className="rounded border border-blue px-2 py-0.5 text-xs text-blue" onClick={() => copy("url", url)}>
                {copied === "url" ? "Copied" : "Copy"}
              </button>
            </>
          ) : (
            <span>Connect your public HTTPS URL (Network section) and the exact URL appears here.</span>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-28 shrink-0">Webhook secret</span>
          {!st.data ? (
            <span role="status">{st.isError ? "Could not load webhook status" : "Loading…"}</span>
          ) : !st.data.secret_set ? (
            <span className="text-goldLight">Not set — run <code>make keys</code> and restart.</span>
          ) : secret ? (
            <>
              <code data-testid="webhook-secret" className="break-all text-goldLight">{secret}</code>
              <button className="rounded border border-blue px-2 py-0.5 text-xs text-blue" onClick={() => copy("secret", secret)}>
                {copied === "secret" ? "Copied" : "Copy"}
              </button>
              <button className="rounded border border-border px-2 py-0.5 text-xs text-blue" onClick={() => setSecret(null)}>Hide</button>
            </>
          ) : (
            <>
              <span>••••••••</span>
              <button className="rounded border border-blue px-2 py-0.5 text-xs text-blue" onClick={() => reveal.mutate()}>Reveal</button>
            </>
          )}
        </div>
        {err && <p role="alert" className="text-goldLight">⚠ {err}</p>}
      </div>

      <h3 className="mt-4 text-sm font-semibold text-gold">Live feeds</h3>
      {st.data && feeds.length === 0 && <p className="text-sm" data-testid="no-feeds">No heartbeats received yet.</p>}
      <ul className="mt-1 grid gap-1 text-sm sm:grid-cols-2">
        {feeds.map((f) => (
          <li key={f.symbol + f.profile} data-testid={`feed-${f.symbol}-${f.profile}`} data-status={f.status}
            className="flex items-center gap-2 rounded-lg border border-border px-3 py-1.5">
            <span aria-hidden className="h-2 w-2 rounded-full"
              style={{ background: f.status === "FRESH" ? badge.ok : f.status === "STALE" ? badge.bad : "transparent", border: "1px solid #1E2A4A" }} />
            <b className="text-gold">{f.symbol} {f.profile}</b>
            <span>{FEED_LABEL[f.status]}</span>
            {f.last_heartbeat && <span className="ml-auto text-xs opacity-75">{etTime(f.last_heartbeat)}</span>}
          </li>
        ))}
      </ul>
      {(Object.keys(accepted).length > 0 || Object.keys(rejected).length > 0) && (
        <p className="mt-2 text-xs" data-testid="webhook-counts">
          Accepted: {Object.entries(accepted).map(([k, v]) => `${k} ${v}`).join(", ") || "0"} · Rejected:{" "}
          {Object.entries(rejected).map(([k, v]) => `${k} ${v}`).join(", ") || "0"}
          {st.data?.last_rejection && <span className="text-goldLight"> · last: {st.data.last_rejection.code} — {st.data.last_rejection.detail}</span>}
        </p>
      )}
    </section>
  );
}
