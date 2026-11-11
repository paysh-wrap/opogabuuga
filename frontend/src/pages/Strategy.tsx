import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { usePageTitle } from "../components/usePageTitle";
import StrategyButtons from "../components/StrategyButtons";
import StrategyPresets from "../components/StrategyPresets";
import TaMgcCard from "../components/TaMgcCard";
import TradingR1Card from "../components/TradingR1Card";
import StrategyGates from "../components/StrategyGates";
import AiLedger from "../components/AiLedger";

interface Feed { profile: string; feed: string; mso_trend: string | null; mso_osc: string | null; last_mso_event: [string, string] | null }
interface S {
  mso_enabled?: boolean;
  tradingagents: { installed_version: string | null; pinned_version: string; configured: boolean; schedule: string };
  instruments: { symbol: string; enabled: boolean; proxy: string; bias: string; feeds: Feed[] }[];
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
      <StrategyPresets />
      <StrategyButtons />
      <TaMgcCard />
      <TradingR1Card />
      <StrategyGates />
      <AiLedger />
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
          <h2 className="font-semibold text-gold">2 · Your TradingView feed</h2>
          {s.instruments.filter((i) => i.enabled).map((i) => (
            <div key={i.symbol} className="mt-2 text-sm">
              <b className="text-gold">{i.symbol}</b>
              {i.feeds.length === 0 && <span> — no TradingView alerts received yet (<Link className="text-blue underline" to="/connections">setup</Link>)</span>}
              {i.feeds.map((f) => (
                <div key={f.profile} className="ml-3">
                  {dot(f.feed === "FRESH")} {f.profile} feed {f.feed}
                  {s.mso_enabled && ` · MSO ${f.mso_trend ?? "—"} ${f.mso_osc ? `(${Number(f.mso_osc).toFixed(1)})` : ""}`}
                  {s.mso_enabled && f.last_mso_event && ` · last ${f.last_mso_event[0]} ${f.last_mso_event[1]}`}
                </div>
              ))}
            </div>
          ))}
        </section>
      </div>
    </div>
  );
}
