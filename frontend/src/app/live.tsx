import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { LiveSocket, wsUrl } from "../lib/ws";
import { browserNotify } from "../lib/notify";

type Handler = (data: Record<string, unknown>) => void;

// §19 WS events → the queries each one makes stale. Pages refresh through React Query; no page opens its own socket.
export const EVENT_QUERIES: Record<string, string[]> = {
  "signal.updated": ["signals", "today", "dashboard", "skips"],
  "approval.created": ["automation"],
  "approval.expired": ["automation"],
  "order.updated": ["automation", "positions", "trades", "journal"],
  "position.updated": ["positions", "dashboard", "trades", "journal", "pnl-daily"],
  "account.updated": ["accounts", "dashboard", "positions"],
  "risk.alert": ["dashboard", "accounts", "automation"],
  "risk.eval_mode.changed": ["eval-mode", "evalmode", "accounts", "dashboard", "risk"],
  "risk.day_lockin": ["dashboard", "accounts"],
  "risk.settings_changed": ["risk", "rules", "lowrisk", "payout-settings", "payout-plan"],
  "cooldown.changed": ["plan", "dashboard"],
  "payout.ready": ["payouts", "payout-plan", "dashboard"],
  "payout.changed": ["payouts", "payout-plan"],
  "automation.changed": ["automation", "accounts", "dashboard"],
  "job.progress": ["jobs", "backtests", "lab"],
  "system.status": ["preflight", "plan", "health"],
  "notification": ["notifications"],
  "connection.updated": ["connections", "webhook-status"],
  "live.changed": ["live", "health"],
};

interface Live {
  up: boolean;
  lastEvent: string | null;
  on: (event: string, h: Handler) => () => void;
}
const LiveCtx = createContext<Live>({ up: false, lastEvent: null, on: () => () => {} });

export function LiveProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const [up, setUp] = useState(false);
  const [lastEvent, setLast] = useState<string | null>(null);
  const sock = useRef<LiveSocket | null>(null);
  if (sock.current === null) sock.current = new LiveSocket(wsUrl());
  useEffect(() => {
    const s = sock.current!;
    s.onStatus = setUp;
    const offs = Object.entries(EVENT_QUERIES).map(([ev, keys]) =>
      s.on(ev, (d) => {
        setLast(`${ev}:${String(d.id ?? d.account ?? d.signal ?? "")}`);
        keys.forEach((k) => void qc.invalidateQueries({ queryKey: [k] }));
      }),
    );
    offs.push(s.on("notification", (d) => browserNotify(String(d.title ?? "Paytience"), String(d.body ?? ""))));
    s.start();
    return () => {
      offs.forEach((f) => f());
      s.stop();
    };
  }, [qc]);
  const on = useCallback((e: string, h: Handler) => sock.current!.on(e, h), []);
  return <LiveCtx.Provider value={{ up, lastEvent, on }}>{children}</LiveCtx.Provider>;
}

export const useLive = () => useContext(LiveCtx);

/** Subscribe a component to one WS event for its lifetime (shared socket). */
export function useLiveEvent(event: string, handler: Handler): void {
  const { on } = useLive();
  const ref = useRef(handler);
  ref.current = handler;
  useEffect(() => on(event, (d) => ref.current(d)), [on, event]);
}
