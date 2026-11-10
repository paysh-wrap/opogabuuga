import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { usePageTitle } from "../components/usePageTitle";
import StrategyButtons from "../components/StrategyButtons";
import GateChain from "../components/GateChain";
import AiLedger from "../components/AiLedger";

interface Feed { profile: string; feed: string; mso_trend: string | null; mso_osc: string | null; active_models: { key: string; dir: string; status: string }[]; last_mso_event: [string, string] | null }
interface S {
  tradingagents: { installed_version: string | null; pinned_version: string; configured: boolean; schedule: string };
  indicators: string[];
  instruments: { symbol: string; enabled: boolean; proxy: string; bias: string; feeds: Feed[] }[];
  gates: { id: string; text: string; last: boolean | null }[];
  last_signal: { id: number; status: string; skip_reason: string | null } | null;
}
const dot = (ok: boolean | null) => <span aria-hidden style={{ color: ok == null ? "#64748B" : ok ? "#22C55E" : "#EF4444" }}>●</span>;
const card = "rounded-xl border border-border bg-card p-4";

export default function Strategy() {
  usePageTitle("Strategy");
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["strategy"], queryFn: () => api<S>("/api/strategy"), refetchInterval: 10000 });
  const runBias = useMutation({ mutationFn: () => api("/api/bias/run", { method: "POST" }), onSettled: () => void qc.invalidateQueries({ queryKey: ["strategy"] }) });
  const s = q.data;
  if (!s) return <p role="status">Loading…</p>;
  const ta = s.tradingagents;
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-gold">Strategy</h1>
      <StrategyButtons />
      <GateChain />
      <AiLedger />
      <p className="text-sm"><b className="text-gold">LunqFX engine (below):</b> no single part trades alone. <b className="text-gold">TradingAgents</b> picks the side for the day (<b className="text-gold">Vibe-Trading</b> can overrule a one-sided day back to both sides when it strongly disagrees; <b className="text-gold">OpenBB</b> supplies the market data both read) · the <b className="text-gold">LunqFX fractal</b> says where (stop) and what (target) · the <b className="text-gold">BigBeluga MSO</b> says when · then gates G1–G8 and risk decide whether and how big.</p>

      <div className="grid gap-4 lg:grid-cols-3">
        <section className={card} data-testid="ta-card">
          <h2 className="font-semibold text-gold">1 · TradingAgents (which side)</h2>
          <p className="text-sm">{dot(!!ta.installed_version)} TauricResearch/TradingAgents {ta.installed_version ? `v${ta.installed_version} installed` : "not installed"} (pinned v{ta.pinned_version})</p>
          <p className="text-sm">{dot(ta.configured)} LLM key {ta.configured ? "set" : <>missing — <Link className="text-blue underline" to="/connections">add it</Link></>}</p>
          <p className="text-sm">Runs daily at {ta.schedule} ET on each proxy ETF.</p>
          {s.instruments.filter((i) => i.enabled).map((i) => (
            <p key={i.symbol} className="text-sm">{i.symbol} ← {i.proxy}: <b className="text-gold">{i.bias}</b></p>
          ))}
          <button className="mt-2 rounded-md border border-blue px-3 py-1 text-sm font-semibold text-blue disabled:opacity-50" disabled={runBias.isPending} onClick={() => runBias.mutate()}>
            {runBias.isPending ? "Running…" : "Run bias now"}
          </button>
        </section>

        <section className={`${card} lg:col-span-2`}>
          <h2 className="font-semibold text-gold">2 · Your TradingView indicators (where · what · when)</h2>
          <ul className="text-sm">{s.indicators.map((n) => <li key={n}>• {n}</li>)}</ul>
          {s.instruments.filter((i) => i.enabled).map((i) => (
            <div key={i.symbol} className="mt-2 text-sm">
              <b className="text-gold">{i.symbol}</b>
              {i.feeds.length === 0 && <span> — no TradingView alerts received yet (<Link className="text-blue underline" to="/connections">setup</Link>)</span>}
              {i.feeds.map((f) => (
                <div key={f.profile} className="ml-3">
                  {dot(f.feed === "FRESH")} {f.profile} feed {f.feed} · MSO {f.mso_trend ?? "—"} {f.mso_osc ? `(${Number(f.mso_osc).toFixed(1)})` : ""}
                  {f.last_mso_event && ` · last ${f.last_mso_event[0]} ${f.last_mso_event[1]}`}
                  {f.active_models.map((m) => <div key={m.key} className="ml-4">fractal model {m.dir}: {m.status}</div>)}
                </div>
              ))}
            </div>
          ))}
        </section>
      </div>

      <section className={card}>
        <h2 className="font-semibold text-gold">3 · Gates (all must pass){s.last_signal && <span className="text-sm font-normal text-blue"> — last signal #{s.last_signal.id}: {s.last_signal.status}{s.last_signal.skip_reason ? ` (${s.last_signal.skip_reason})` : ""}</span>}</h2>
        <ul className="mt-2 grid gap-1 text-sm sm:grid-cols-2">
          {s.gates.map((g) => <li key={g.id} data-testid={`gate-${g.id}`}>{dot(g.last)} <b>{g.id}</b> {g.text}</li>)}
        </ul>
      </section>
    </div>
  );
}
