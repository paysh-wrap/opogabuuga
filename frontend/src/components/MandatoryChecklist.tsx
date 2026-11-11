import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, type ConnectionsResponse, type WebhookStatus } from "../lib/api";
import { badge } from "../lib/theme";
import { buildChecklist, type CheckState, type PlanSlice } from "../lib/mandatory";

const MARK: Record<CheckState, { dot: string; word: string }> = {
  ok: { dot: badge.ok, word: "OK" },
  fail: { dot: badge.bad, word: "MISSING" },
  unknown: { dot: "transparent", word: "UNKNOWN" },
};

/** D93: live checklist of the connections that are mandatory to trade EVAL/LIVE. Read-only; reuses the shared
 * react-query keys so it adds no extra polling where those queries already run. */
export default function MandatoryChecklist({ compact = false }: { compact?: boolean }) {
  const conns = useQuery({ queryKey: ["connections"], queryFn: () => api<ConnectionsResponse>("/api/connections"), refetchInterval: 30_000 });
  const hook = useQuery({ queryKey: ["webhook-status"], queryFn: () => api<WebhookStatus>("/api/webhook/status"), refetchInterval: 15_000 });
  const plan = useQuery({ queryKey: ["plan"], queryFn: () => api<PlanSlice>("/api/today/plan"), refetchInterval: 15_000 });
  const { items, ready } = buildChecklist({ conns: conns.data, webhook: hook.data, plan: plan.data });
  const unknown = items.filter((i) => i.state === "unknown").length;

  return (
    <section data-testid="mandatory-checklist" className="mission-tile mandatory-panel rounded-xl border bg-card p-4">
      <h2 className="font-semibold text-gold">Mandatory connection checklist <span className="tile-aside">EVAL / LIVE</span></h2>
      <p data-testid="ready-line" data-ready={ready} className="ready-line mt-1 text-sm font-semibold">
        Ready to trade EVAL/LIVE:{" "}
        {ready === "yes" && <b className="text-mandatory">YES</b>}
        {ready === "no" && <b className="text-mandatory">NO</b>}
        {ready === "unconfirmed" && <b className="text-mandatory">NOT CONFIRMED</b>}
        <span className="font-normal text-blueLight">
          {ready === "no" && ` — ${items.filter((i) => i.state === "fail").length} mandatory item(s) missing`}
          {ready === "unconfirmed" && ` — nothing missing, but ${unknown} item(s) cannot be confirmed from the API`}
        </span>
      </p>
      <ul className={`mt-2 grid gap-x-4 ${compact ? "" : "md:grid-cols-2"}`}>
        {items.map((i) => (
          <li key={i.id} data-testid={`check-${i.id}`} data-state={i.state} className="check-row">
            <span aria-hidden className="check-dot" style={{ background: MARK[i.state].dot }} />
            <span className="min-w-0">
              <span className="text-mandatory font-semibold">{i.label}</span>{" "}
              <span className="check-word">{MARK[i.state].word}</span>
              <span className="block text-xs text-blueLight">{i.detail}</span>
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-2 text-xs text-blueLight">
        Paper accounts trade without the broker route. Optional (not listed): Discord, AI keys, Trading-R1, data vendors.{" "}
        <Link to="/connections" className="text-blue underline">Set up connections</Link>
      </p>
    </section>
  );
}
