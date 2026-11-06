import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";

/** §18 Connections "test alert": paste a TradingView alert message; the server parses it and checks the secret.
 *  Dry run — nothing is stored, no heartbeat or signal is recorded. */
export default function TestAlert() {
  const [text, setText] = useState("");
  const t = useMutation({
    mutationFn: () => api<{ ok: boolean; code: string; detail: string }>("/api/webhook/test-alert", { method: "POST", body: text, headers: { "content-type": "text/plain" } }),
  });
  return (
    <section data-testid="test-alert" className="rounded-xl border border-border bg-card p-4">
      <h2 className="font-semibold text-gold">Test alert</h2>
      <p className="text-xs">Paste the alert message from a TradingView alert (or the bridge script). Checked here only — nothing is stored.</p>
      <textarea aria-label="Alert message" className="mt-2 h-24 w-full" value={text} onChange={(e) => setText(e.target.value)} />
      <button className="mt-2 rounded-md border border-blue px-3 py-1.5 text-sm font-semibold text-blue disabled:opacity-50" disabled={!text || t.isPending} onClick={() => t.mutate()}>
        {t.isPending ? "Checking…" : "Check alert"}</button>
      {t.data && <p role="status" data-testid="test-alert-result" className="mt-2 text-sm text-goldLight">{t.data.ok ? "✓ Valid: " : `⚠ ${t.data.code}: `}{t.data.detail}</p>}
      {t.error && <p role="alert" className="mt-2 text-sm text-goldLight">⚠ {t.error instanceof ApiError ? t.error.message : "Request failed"}</p>}
    </section>
  );
}
