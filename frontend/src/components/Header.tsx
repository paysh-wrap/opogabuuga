import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api, type ConnectionsResponse, type Health } from "../lib/api";
import { useLive } from "../app/live";
import HeaderStatus from "./HeaderStatus";
import { AlertsBell, JobsIndicator } from "./HeaderAlerts";

function useEtClock(): string {
  const fmt = () =>
    new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", hour: "2-digit", minute: "2-digit",
      second: "2-digit", hour12: false }).format(new Date());
  const [t, setT] = useState(fmt);
  useEffect(() => {
    const id = setInterval(() => setT(fmt()), 1000);
    return () => clearInterval(id);
  }, []);
  return t;
}

export default function Header() {
  const clock = useEtClock();
  const { up } = useLive();
  const qc = useQueryClient();
  const nav = useNavigate();
  const health = useQuery({ queryKey: ["health"], queryFn: () => api<Health>("/api/health"), refetchInterval: 15_000 });
  const conns = useQuery({ queryKey: ["connections"], queryFn: () => api<ConnectionsResponse>("/api/connections") });
  const s = conns.data?.summary;
  const risk = useQuery({ queryKey: ["risk"], queryFn: () => api<{ settings: Record<string, unknown> }>("/api/risk/settings") });
  const low = useQuery({ queryKey: ["lowrisk"], queryFn: () => api<{ enabled: boolean }>("/api/risk/low-risk") });
  const rs = risk.data?.settings;
  const tradeMode = !rs ? null : rs["scalp_mode.enabled"] === true ? "Scalp" : rs["one_to_one_mode.enabled"] === true ? "1:1" : "Intraday";

  async function logout() {
    await api("/api/auth/logout", { method: "POST" });
    qc.clear();
    nav("/login");
  }

  return (
    <header className="border-b border-border bg-card">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
        <span data-testid="brand" className="flex items-center gap-2 text-xl font-bold tracking-wide text-gold">
          <span aria-hidden className="grid h-7 w-7 place-items-center rounded-md border border-gold/60 text-sm">P</span>
          Paytience
        </span>
        <span data-testid="mode" className="rounded border border-border px-2 py-0.5 text-xs font-semibold text-goldLight">
          {health.data?.mode ?? "…"}
        </span>
        {tradeMode && (
          <a href="/risk" data-testid="trade-mode" title="Trading mode (change on the Risk page)"
            className="rounded-full border border-gold/50 bg-gold/10 px-2.5 py-0.5 text-xs font-semibold text-gold hover:text-goldLight">
            {tradeMode}{low.data?.enabled ? " · Lower risk" : ""}
          </a>
        )}
        {s && (
          <span data-testid="conn-summary" className="text-xs text-blueLight">
            Connections <b className="text-gold">{s.connected}/{s.total}</b>
            {s.required_ready ? " · ready" : " · required missing"}
          </span>
        )}
        <HeaderStatus />
        <span className="ml-auto font-mono text-sm text-goldLight" aria-label="Eastern time">{clock} ET</span>
        <JobsIndicator />
        <AlertsBell />
        <span className="text-xs text-blueLight" title="Live updates">
          <span aria-hidden className="mr-1 inline-block h-2 w-2 rounded-full" style={{ background: up ? "#22C55E" : "#EF4444" }} />
          {up ? "live" : "reconnecting"}
        </span>
        <button onClick={logout} className="rounded border border-blue px-2 py-1 text-xs text-blue hover:text-blueLight">
          Log out
        </button>
      </div>
    </header>
  );
}
