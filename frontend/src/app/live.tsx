import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { LiveSocket, wsUrl } from "../lib/ws";

const LiveCtx = createContext<{ up: boolean; lastEvent: string | null }>({ up: false, lastEvent: null });

export function LiveProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const [up, setUp] = useState(false);
  const [lastEvent, setLast] = useState<string | null>(null);
  useEffect(() => {
    const s = new LiveSocket(wsUrl());
    s.onStatus = setUp;
    s.on("connection.updated", (d) => {
      setLast(`connection.updated:${String(d.id)}:${String(d.status ?? "")}`);
      void qc.invalidateQueries({ queryKey: ["connections"] });
    });
    s.start();
    return () => s.stop();
  }, [qc]);
  return <LiveCtx.Provider value={{ up, lastEvent }}>{children}</LiveCtx.Provider>;
}

export const useLive = () => useContext(LiveCtx);
