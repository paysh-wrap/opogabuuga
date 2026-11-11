import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../lib/api";

export interface UpdateCheck {
  available: boolean;
  commit?: string | null;
  published_at?: string;
  checked_at?: string;
  error: string;
  reason?: string;
}
export interface UpdateStatus {
  version: { commit: string; built_at: string };
  desktop: boolean;
  token_set: boolean;
  last_check: UpdateCheck | null;
  failed_update: string | null;
  blocked: string | null;
}

const box = "rounded-lg border border-gold bg-card p-3 text-sm text-goldLight";
const btn = "rounded-md border border-gold px-3 py-1 text-sm text-gold disabled:opacity-50";

function useUpdates() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["updates"], queryFn: () => api<UpdateStatus>("/api/updates"), refetchInterval: 60_000 });
  const check = useMutation({
    mutationFn: () => api<UpdateCheck>("/api/updates/check", { method: "POST" }),
    onSettled: () => qc.invalidateQueries({ queryKey: ["updates"] }),
  });
  const install = useMutation({ mutationFn: () => api<{ ok: boolean }>("/api/updates/install", { method: "POST" }) });
  const dismiss = useMutation({
    mutationFn: () => api("/api/updates/dismiss-failure", { method: "POST" }),
    onSettled: () => qc.invalidateQueries({ queryKey: ["updates"] }),
  });
  return { q, check, install, dismiss };
}

/** After "Install now": explains what happens and reloads the page by itself once the NEW server answers. */
/** D103: same name the desktop app opens (desktop/paytience_app.py ui_url): paytience-<commit7>-<built_at digits>.localhost. */
export function uiOrigin(commit?: string, builtAt?: string, loc: { port: string; protocol: string } = window.location): string | null {
  if (!commit || commit === "dev") return null;
  const stamp = (builtAt ?? "").replace(/\D/g, "").slice(0, 12);
  return `${loc.protocol}//paytience-${commit.slice(0, 7)}${stamp ? "-" + stamp : ""}.localhost:${loc.port || "8000"}/`;
}

function RestartNotice() {
  const [waited, setWaited] = useState(0);
  useEffect(() => {
    let sawDown = false;
    let stopped = false;
    const t = window.setInterval(async () => {
      if (stopped) return;
      setWaited((w) => w + 2);
      try {
        const r = await fetch("/api/health", { cache: "no-store" });
        if (r.ok && sawDown) {
          stopped = true;
          const b = ((await r.json().catch(() => ({}))) as { build?: { commit?: string; built_at?: string } }).build;
          const target = uiOrigin(b?.commit, b?.built_at, window.location);
          if (target) window.location.href = target; // D103: the NEW build lives under its own browser name
          else window.location.reload();
        }
      } catch {
        sawDown = true; // old server is gone; the new one is starting
      }
    }, 2000);
    return () => window.clearInterval(t);
  }, []);
  return (
    <div data-testid="update-restart-notice" className="mt-2">
      <b className="text-gold">Installing the update — a NEW Paytience server is starting.</b> The old window closes and a new one
      opens in about 30–60 seconds ({waited}s). This page reloads by itself when the new server is ready; if it says it cannot
      connect, just wait. A black window may flash — leave it alone. If nothing has appeared after 3 minutes
      {waited >= 180 ? " (now)" : ""}: open Task Manager, end <b>Paytience</b>, then start Paytience again — your old version is restored
      automatically if the update fails.
    </div>
  );
}

/** D88: "Update available — Install now?" banner. Checks once on start (desktop app + token only). Never auto-installs. */
export function UpdateBanner() {
  const { q, check, install, dismiss } = useUpdates();
  const started = useRef(false);
  const d = q.data;
  useEffect(() => {
    if (d && d.desktop && d.token_set && !d.last_check && !started.current) {
      started.current = true;
      check.mutate();
    }
  }, [d, check]);
  if (!d || !d.version) return null;
  const items: JSX.Element[] = [];
  if (d.failed_update)
    items.push(
      <div key="failed" role="alert" data-testid="banner-update-failed" className={box}>
        ⚠ <b className="text-gold">{d.failed_update}</b>{" "}
        <button className={btn} onClick={() => dismiss.mutate()}>Dismiss</button>
      </div>,
    );
  if (d.last_check?.error)
    items.push(
      <div key="err" role="alert" data-testid="banner-update-error" className={box}>
        ⚠ <b className="text-gold">Update check failed:</b> {d.last_check.error}. The current version keeps running.
      </div>,
    );
  if (d.last_check?.available)
    items.push(
      <div key="avail" role="alert" data-testid="banner-update" className={box}>
        <b className="text-gold">Update available — Install now?</b> (version {d.last_check.commit?.slice(0, 7)}){" "}
        {d.blocked ? (
          <span data-testid="update-blocked">Blocked: {d.blocked}.</span>
        ) : (
          <button className={btn} disabled={install.isPending || install.isSuccess} onClick={() => install.mutate()}>
            {install.isPending ? "Downloading…" : install.isSuccess ? "Restarting…" : "Install now"}
          </button>
        )}
        {install.isSuccess && <RestartNotice />}
        {install.error && <span className="ml-2">⚠ {(install.error as Error).message} — old version kept.</span>}
      </div>,
    );
  return items.length ? <div className="mb-4 space-y-2">{items}</div> : null;
}

/** Settings: version + "Check for updates". */
export function UpdatePanel() {
  const { q, check } = useUpdates();
  const [msg, setMsg] = useState("");
  const d = q.data;
  return (
    <section className="rounded-xl border border-border bg-card p-4">
      <h2 className="font-semibold text-gold">App version</h2>
      {d?.version && (
        <p data-testid="app-version" className="mt-1 text-sm">
          Version <b className="font-mono text-gold">{d.version.commit.slice(0, 7)}</b>
          {d.version.built_at && <> · built {d.version.built_at}</>}
          {!d.desktop && " · (not the desktop app: updates are installed by the Windows app only)"}
        </p>
      )}
      <div className="mt-2 flex items-center gap-3 text-sm">
        <button
          className={btn}
          disabled={check.isPending}
          onClick={() =>
            check.mutate(undefined, {
              onSuccess: (r) =>
                setMsg(r.reason === "no_token" ? "No GitHub token saved — add it on Connections (optional)." : r.available ? "Update available (see banner)." : "You have the latest version."),
              onError: (e) => setMsg(`⚠ ${(e as Error).message}`),
            })
          }
        >
          {check.isPending ? "Checking…" : "Check for updates"}
        </button>
        {msg && <span data-testid="update-msg">{msg}</span>}
        {d && !d.token_set && <Link to="/connections" className="text-blue underline">Add GitHub token</Link>}
      </div>
    </section>
  );
}
