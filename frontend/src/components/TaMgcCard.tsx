import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { StrategiesResp } from "./StrategyButtons";

// D84: the TradingAgents MGC research (part of the AI Duo button): latest report + the structured setup it produced,
// Vibe-Trading's opinion, and today's decision with its reason code. Uses the existing TradingAgents connection.
const card = "rounded-xl border border-border bg-card p-4";

export default function TaMgcCard() {
  const q = useQuery({ queryKey: ["strategies"], queryFn: () => api<StrategiesResp>("/api/strategies"), refetchInterval: 30000 });
  const t = q.data?.ta_mgc;
  if (!t) return null;
  const r = t.research;
  const s = r?.setup;
  return (
    <section className={card} data-testid="ta-mgc">
      <h2 className="font-semibold text-gold">TradingAgents MGC research (part of AI Duo) — paper only</h2>
      <p className="text-xs text-blue">Gold drivers (US dollar, real yields, Fed/CPI, risk sentiment, trend and levels) → one setup a day, taken only if Vibe-Trading agrees on the side. Stop beyond the invalidation, target about 2R (1:2 preferred, never below 1.5R), 1 micro, 03:00–11:30 ET.</p>
      {!t.connected && <p className="mt-2 text-sm text-gold" data-testid="ta-mgc-key">{t.message ?? "AI key not connected"} — nothing runs until the TradingAgents key is saved on the API Keys page.</p>}
      {t.connected && !t.enabled && <p className="mt-2 text-sm text-blue">Off — turn on the AI Duo button (with MGC in its markets) to run the research each morning.</p>}
      {r ? (
        <div className="mt-2 text-sm" data-testid="ta-mgc-research">
          <p>Report of <b className="text-gold">{r.day}</b> · call <b className="text-gold">{r.label}</b>{r.error && <> · <span className="text-gold">failed: {r.error}</span></>}</p>
          {s && s.side && (
            <p data-testid="ta-mgc-setup">
              Setup: <b className="text-gold">{s.side}</b>{s.confidence != null && ` (${s.confidence}%)`}
              {s.entry_low != null && <> · zone {s.entry_low}–{s.entry_high}</>}{s.invalidation != null && <> · invalidation {s.invalidation}</>}{s.target != null && <> · target {s.target}</>}{s.valid_until && <> · valid until {s.valid_until} ET</>}
            </p>
          )}
          {s?.reasons && s.reasons.length > 0 && <ul className="list-disc pl-5 text-blue">{s.reasons.map((x) => <li key={x}>{x}</li>)}</ul>}
          <p data-testid="ta-mgc-vt">Vibe-Trading: <b className="text-gold">{r.vt ? `${r.vt.direction} ${r.vt.confidence}%` : "no opinion"}</b>{r.vt_note && <span className="text-blue"> ({r.vt_note})</span>}</p>
        </div>
      ) : (
        t.connected && <p className="mt-2 text-sm text-blue">No research report yet.</p>
      )}
      {t.decision && (
        <p className="mt-2 text-sm" data-testid="ta-mgc-decision">
          MGC decision {t.decision.day}: <b className="text-gold">{t.decision.status === "PASS" ? `TRADE ${t.decision.direction}` : "NO TRADE"}</b> · {t.decision.code} · {t.decision.mode === "RESEARCH" ? "from the research setup" : "from the daily AI call"}{t.decision.below_preferred_2r ? " · below preferred 2R" : ""}
        </p>
      )}
    </section>
  );
}
