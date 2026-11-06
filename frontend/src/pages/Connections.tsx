import { useState, type FormEvent } from "react";
import AiPricing from "../components/AiPricing";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, type Connection, type ConnectionsResponse, type Indicator } from "../lib/api";
import StatusBadge from "../components/StatusBadge";
import { usePageTitle } from "../components/usePageTitle";
import TradingViewSetup from "../components/TradingViewSetup";
import TestAlert from "../components/TestAlert";
import { etDateTime } from "../lib/time";

const GROUPS: [string, string][] = [
  ["signals", "Signals"],
  ["ai_bias", "AI bias — TradingAgents"],
  ["broker", "Broker / order route"],
  ["data", "Market data & calendar"],
  ["notifications", "Notifications"],
  ["network", "Network"],
  ["firm", "Prop firm"],
];

function ExtLink({ href, children }: { href: string; children: string }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 underline-offset-2 hover:underline">
      {children} <span aria-hidden>↗</span>
    </a>
  );
}

function ConnectionCard({ c }: { c: Connection }) {
  const qc = useQueryClient();
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(c.fields.filter((f) => f.kind !== "secret").map((f) => [f.name, c.hints[f.name] ?? (f.kind === "select" ? f.options[0] ?? "" : "")])),
  );
  const [error, setError] = useState("");
  const refresh = () => qc.invalidateQueries({ queryKey: ["connections"] });
  const onErr = (e: unknown) => setError(e instanceof ApiError ? e.message : "Request failed");

  const save = useMutation({
    mutationFn: () => api<Connection>(`/api/connections/${c.id}`, { method: "PUT", body: JSON.stringify({ values }) }),
    onMutate: () => setError(""),
    onSuccess: () => {
      setValues((v) => Object.fromEntries(Object.entries(v).filter(([k]) => c.fields.find((f) => f.name === k)?.kind !== "secret")));
      void refresh();
    },
    onError: onErr,
  });
  const retest = useMutation({
    mutationFn: () => api<Connection>(`/api/connections/${c.id}/test`, { method: "POST" }),
    onSuccess: () => void refresh(),
    onError: onErr,
  });
  const remove = useMutation({
    mutationFn: () => api<Connection>(`/api/connections/${c.id}`, { method: "DELETE" }),
    onSuccess: () => { setValues({}); void refresh(); },
    onError: onErr,
  });

  const connected = c.status === "connected";
  const selectedLlm = values.llm_provider || c.hints.llm_provider;
  const llmKeyUrl = selectedLlm ? c.llm_key_urls?.[selectedLlm] : undefined;
  const busy = save.isPending || retest.isPending || remove.isPending;

  function submit(e: FormEvent) {
    e.preventDefault();
    save.mutate();
  }

  return (
    <article data-testid={`conn-${c.id}`} data-status={c.status}
      className={`rounded-xl border bg-card p-4 transition-all duration-300 hover:border-blue/60 ${connected ? "border-gold shadow-[0_0_0_1px_#D4AF37,0_0_24px_-8px_#D4AF37]" : "border-border"}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="font-semibold text-gold">{c.name}{c.required && <span className="ml-2 text-xs text-goldLight">required</span>}</h3>
        <StatusBadge status={c.status} />
      </div>
      <p className="mt-1 text-sm">{c.purpose}</p>
      {c.detail && <p data-testid="detail" className={`mt-1 text-sm ${connected ? "text-goldLight" : "text-blueLight"}`}>{connected ? "✓ " : ""}{c.detail}</p>}

      {c.id === "tradingagents" && (
        <dl className="mt-2 grid grid-cols-[auto,1fr] gap-x-3 text-xs">
          <dt>Installed</dt><dd data-testid="ta-installed" className="text-gold">{c.installed_version ?? `not installed (${c.install_error ?? "?"})`}</dd>
          <dt>Pinned</dt><dd>v{c.pinned_version} · {c.pinned_commit?.slice(0, 10)}</dd>
          <dt>Latest on GitHub</dt><dd>{c.latest_tag ?? "unknown"}{c.latest_tag && c.latest_tag !== `v${c.pinned_version}` ? " — newer release exists; upgrading needs a reviewed pin change" : ""}</dd>
        </dl>
      )}

      {c.steps.length > 0 && (
        <ol className="mt-2 list-decimal space-y-0.5 pl-5 text-xs">{c.steps.map((s) => <li key={s}>{s}</li>)}</ol>
      )}

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm">
        {c.links.map((l) => <ExtLink key={l.url + l.label} href={l.url}>{l.label}</ExtLink>)}
        {llmKeyUrl && !c.links.some((l) => l.url === llmKeyUrl) && <ExtLink href={llmKeyUrl}>{`Get ${selectedLlm} API key`}</ExtLink>}
      </div>
      {c.note && <p className="mt-2 text-xs text-goldLight">{c.note}</p>}

      {c.fields.length > 0 && (
        <form onSubmit={submit} className={`mt-3 grid gap-2 ${c.fields.length > 1 ? "sm:grid-cols-2" : ""}`} autoComplete="off">
          {c.fields.map((f) => {
            const saved = c.hints[f.name];
            const id = `${c.id}-${f.name}`;
            return (
              <label key={f.name} htmlFor={id} className="text-xs">
                {f.label}{f.required ? "" : " (optional)"}
                {f.kind === "select" ? (
                  <select id={id} className="mt-1 w-full" value={values[f.name] ?? ""}
                    onChange={(e) => setValues({ ...values, [f.name]: e.target.value })}>
                    <option value="">Choose…</option>
                    {f.options.map((o) => <option key={o} value={o}>{o}</option>)}
                  </select>
                ) : (
                  <input id={id} className="mt-1 w-full" type={f.kind === "secret" ? "password" : "text"}
                    autoComplete={f.kind === "secret" ? "new-password" : "off"} spellCheck={false}
                    placeholder={f.kind === "secret" && saved ? `saved ${saved} — leave blank to keep` : f.placeholder}
                    value={values[f.name] ?? ""} onChange={(e) => setValues({ ...values, [f.name]: e.target.value })} />
                )}
                {f.help && <span className="mt-0.5 block opacity-75">{f.help}</span>}
              </label>
            );
          })}
          <div className="flex flex-wrap items-center gap-2 sm:col-span-2 pt-1">
            <button type="submit" disabled={busy}
              className="rounded-md border border-blue bg-blue/10 px-3 py-1.5 text-sm font-semibold text-blue disabled:opacity-50">
              {save.isPending ? (c.testable ? "Testing…" : "Saving…") : c.testable ? "Save & Test" : "Save"}
            </button>
            {c.status !== "not_set" && c.testable && (
              <button type="button" disabled={busy} onClick={() => retest.mutate()}
                className="rounded-md border border-border px-3 py-1.5 text-sm text-blue disabled:opacity-50">
                {retest.isPending ? "Testing…" : "Re-test"}
              </button>
            )}
            {c.status !== "not_set" && (
              <button type="button" disabled={busy}
                onClick={() => window.confirm(`Remove saved ${c.name} credentials?`) && remove.mutate()}
                className="rounded-md border border-border px-3 py-1.5 text-sm text-blue disabled:opacity-50">
                Remove
              </button>
            )}
            {c.tested_at && <span className="text-xs opacity-75">tested {etDateTime(c.tested_at)}</span>}
          </div>
          {error && <p role="alert" className="text-sm text-goldLight sm:col-span-2">⚠ {error}</p>}
        </form>
      )}
    </article>
  );
}

function IndicatorCard({ ind }: { ind: Indicator }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [src, setSrc] = useState("");
  const [err, setErr] = useState("");
  const save = useMutation({
    mutationFn: () => api(`/api/indicators/${ind.id}`, { method: "PUT", body: JSON.stringify({ source: src }) }),
    onSuccess: () => { setSrc(""); setOpen(false); setErr(""); void qc.invalidateQueries({ queryKey: ["connections"] }); },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Request failed"),
  });
  const ok = ind.alerts_status === "connected";
  return (
    <article data-testid={`ind-${ind.id}`} className={`rounded-xl border bg-card p-4 ${ok ? "border-gold" : "border-border"}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="font-semibold text-gold">{ind.name}</h3>
        <StatusBadge status={ind.alerts_status} />
      </div>
      <p className="mt-1 text-sm">Role: {ind.role}</p>
      <p className="text-xs">Required setting: <span className="text-goldLight">{ind.setting}</span></p>
      <p className="mt-1 text-xs">{ind.alerts_detail}</p>
      <p className="mt-1 text-xs">
        Pine source: {ind.source_on_file
          ? <span className="text-gold">on file · license {ind.license}{ind.personal_use_only ? " · PERSONAL USE ONLY" : ""}</span>
          : "not provided yet (needed to port it into Paytience_Bridge — paste it, never scraped)"}
      </p>
      <div className="mt-2 flex flex-wrap gap-4 text-sm">
        <ExtLink href={ind.link}>Find on TradingView</ExtLink>
        <button className="text-blue underline-offset-2 hover:underline" onClick={() => setOpen(!open)}>
          {ind.source_on_file ? "Replace source" : "Paste Pine source + license"}
        </button>
      </div>
      {open && (
        <div className="mt-2 space-y-2">
          <textarea aria-label={`${ind.name} source`} className="h-40 w-full font-mono text-xs" value={src}
            onChange={(e) => setSrc(e.target.value)} placeholder="// license header…&#10;//@version=6&#10;indicator(…)" />
          <button disabled={save.isPending || src.length < 10} onClick={() => save.mutate()}
            className="rounded-md border border-blue bg-blue/10 px-3 py-1.5 text-sm font-semibold text-blue disabled:opacity-50">
            Save source
          </button>
          {err && <p role="alert" className="text-sm text-goldLight">⚠ {err}</p>}
        </div>
      )}
    </article>
  );
}

export default function Connections() {
  usePageTitle("Connections");
  const q = useQuery({ queryKey: ["connections"], queryFn: () => api<ConnectionsResponse>("/api/connections"), refetchInterval: 30_000 });
  if (q.isLoading) return <p role="status">Loading connections…</p>;
  if (q.error || !q.data) return <p role="alert">Could not load connections: {String(q.error?.message ?? "unknown")}</p>;
  const { connections, indicators, summary, master_key_set } = q.data;
  const tunnel = connections.find((c) => c.id === "tunnel");
  const base = tunnel?.status === "connected" ? tunnel.hints.public_url : undefined;
  const required = connections.filter((c) => c.required);

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-bold text-gold">Connections &amp; API keys</h1>
        <p className="mt-1 text-sm">Where to log in, where to get each key, and live status. Keys are encrypted, never shown again, and each card turns gold once its live test passes.</p>
        <div className="mt-4 rounded-xl border border-border bg-card p-3">
          <div className="flex items-center justify-between text-sm">
            <span>Setup progress</span>
            <b className="text-gold" data-testid="summary-count">{summary.connected}/{summary.total}</b>
          </div>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-bg" role="progressbar" aria-label="Setup progress"
            aria-valuemin={0} aria-valuemax={summary.total} aria-valuenow={summary.connected}>
            <div className="h-full rounded-full bg-gradient-to-r from-gold to-goldLight transition-all duration-500"
              style={{ width: `${summary.total ? (100 * summary.connected) / summary.total : 0}%` }} />
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-3 text-sm">
          {required.map((r) => (
            <span key={r.id} className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2">
              {r.name.split(" (")[0]!.split(" —")[0]} <StatusBadge status={r.status} />
            </span>
          ))}
        </div>
        {!master_key_set && (
          <p role="alert" className="mt-3 rounded-lg border border-gold bg-card p-3 text-sm text-goldLight">
            ⚠ Master encryption key is not set, so keys can't be saved. Run <code>make keys</code>, add the output to <code>.env</code>, then restart.
          </p>
        )}
      </section>

      <TradingViewSetup publicBase={base} />
      <TestAlert />

      <section>
        <h2 className="mb-2 text-lg font-semibold text-gold">TradingView indicators</h2>
        <div className="grid gap-3 md:grid-cols-2">{indicators.map((i) => <IndicatorCard key={i.id} ind={i} />)}</div>
      </section>

      {GROUPS.map(([cat, title]) => {
        const items = connections.filter((c) => c.category === cat);
        if (!items.length) return null;
        return (
          <section key={cat}>
            <h2 className="mb-2 text-lg font-semibold text-gold">{title}</h2>
            <div className="grid gap-3 md:grid-cols-2">{items.map((c) => <ConnectionCard key={c.id} c={c} />)}</div>
          </section>
        );
      })}
      <AiPricing />
    </div>
  );
}
