import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { etDateTime } from "../lib/time";

export interface Job { id: string; kind: string; label: string; status: string; progress: number; at: string }
export interface Notice { id: number; level: string; kind: string; title: string; body: string; created_at: string; read: boolean }

const pill = "rounded-full border px-2.5 py-0.5 text-xs font-semibold";

/** Header jobs indicator (§18): running backtests / Lab / scheduled jobs — refreshed by job.progress events. */
export function JobsIndicator() {
  const [open, setOpen] = useState(false);
  const q = useQuery({ queryKey: ["jobs"], queryFn: () => api<{ jobs: Job[] }>("/api/jobs"), refetchInterval: 60_000 });
  const jobs = q.data?.jobs ?? [];
  return (
    <span className="relative">
      <button data-testid="jobs" aria-expanded={open} onClick={() => setOpen(!open)}
        className={`${pill} ${jobs.length ? "border-gold text-gold" : "border-border text-blueLight"}`}
        title="Background jobs">
        {jobs.length ? `⟳ ${jobs.length} job${jobs.length > 1 ? "s" : ""}` : "No jobs"}
      </button>
      {open && (
        <div role="dialog" aria-label="Running jobs" className="absolute right-0 z-20 mt-2 w-72 rounded-lg border border-border bg-card p-3 text-sm shadow-lg">
          {q.error && <p role="alert" className="text-goldLight">⚠ Cannot load jobs.</p>}
          {!q.error && jobs.length === 0 && <p>Nothing running.</p>}
          <ul className="space-y-2">
            {jobs.map((j) => (
              <li key={j.id} data-testid={`job-${j.id}`}>
                <span className="text-gold">{j.label}</span> <span className="text-xs">({j.kind}, {j.status})</span>
                <div className="mt-1 h-1.5 rounded bg-border"><div className="h-1.5 rounded bg-blue" style={{ width: `${j.progress}%` }} /></div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </span>
  );
}

/** Alerts bell (§18): unread in-app notifications, mark one / all read. */
export function AlertsBell() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const q = useQuery({
    queryKey: ["notifications"],
    queryFn: () => api<{ notifications: Notice[]; unread: number }>("/api/notifications?limit=30"),
    refetchInterval: 60_000,
  });
  const mark = useMutation({
    mutationFn: (ids: number[] | null) => api("/api/notifications/read", { method: "POST", body: JSON.stringify(ids ? { ids } : {}) }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["notifications"] }),
  });
  const unread = q.data?.unread ?? 0;
  return (
    <span className="relative">
      <button data-testid="alerts" aria-expanded={open} aria-label={`Alerts, ${unread} unread`} onClick={() => setOpen(!open)}
        className={`${pill} ${unread ? "border-gold bg-gold/10 text-gold" : "border-border text-blueLight"}`}>
        🔔 {unread > 0 && <b data-testid="alerts-count">{unread}</b>}
      </button>
      {open && (
        <div role="dialog" aria-label="Alerts" className="absolute right-0 z-20 mt-2 max-h-96 w-80 overflow-y-auto rounded-lg border border-border bg-card p-3 text-sm shadow-lg">
          <div className="mb-2 flex items-center justify-between">
            <b className="text-gold">Alerts</b>
            <button className="text-xs text-blue underline disabled:opacity-50" disabled={!unread || mark.isPending} onClick={() => mark.mutate(null)}>Mark all read</button>
          </div>
          {q.isLoading && <p role="status">Loading…</p>}
          {q.error && <p role="alert" className="text-goldLight">⚠ Cannot load alerts.</p>}
          {q.data?.notifications.length === 0 && <p>No alerts.</p>}
          <ul className="space-y-2">
            {q.data?.notifications.map((n) => (
              <li key={n.id} data-testid={`alert-${n.id}`} className={`border-t border-border pt-1 ${n.read ? "opacity-60" : ""}`}>
                <span aria-hidden className="mr-1 inline-block h-2 w-2 rounded-full"
                  style={{ background: n.level === "error" ? "#EF4444" : n.level === "warn" ? "#D4AF37" : "#22C55E" }} />
                <b className="text-gold">{n.title}</b>
                {n.body && <p className="text-xs">{n.body}</p>}
                <p className="text-xs opacity-75">{etDateTime(n.created_at)}
                  {!n.read && <button className="ml-2 text-blue underline" onClick={() => mark.mutate([n.id])}>Mark read</button>}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </span>
  );
}
