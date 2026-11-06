import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { fmtCountdown, secondsToEt } from "../lib/flatten";

interface Acct { id: number; armed: boolean; selected: boolean }
const KILL_PHRASE = "KILL"; // must match backend KILL_PHRASE

function useNow(): Date {
  const [n, setN] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setN(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return n;
}

function modeLabel(m: string): string {
  return m.startsWith("SEMI") ? "SEMI" : m.startsWith("FULL") ? "FULL" : "OFF";
}

/** §18 header extras: Automation mode, Eval Mode, "Trading N of M", flatten countdown, KILL SWITCH. */
export default function HeaderStatus() {
  const qc = useQueryClient();
  const now = useNow();
  const auto = useQuery({ queryKey: ["automation"], queryFn: () => api<{ mode: string }>("/api/automation"), refetchInterval: 10_000 });
  const ev = useQuery({ queryKey: ["eval-mode"], queryFn: () => api<{ enabled: boolean }>("/api/risk/eval-mode") });
  const accts = useQuery({ queryKey: ["accounts"], queryFn: () => api<{ accounts: Acct[] }>("/api/accounts"), refetchInterval: 15_000 });
  const rules = useQuery({ queryKey: ["rules"], queryFn: () => api<{ rules: { internal: { auto_flatten: string } } }>("/api/rules"), staleTime: 300_000 });
  const [open, setOpen] = useState(false);
  const [typed, setTyped] = useState("");
  const [err, setErr] = useState("");
  const kill = useMutation({
    mutationFn: () => api("/api/kill-switch", { method: "POST", body: JSON.stringify({ confirm: typed }) }),
    onSuccess: () => { setOpen(false); setTyped(""); setErr(""); void qc.invalidateQueries(); },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Kill switch request failed"),
  });

  const list = accts.data?.accounts;
  const trading = list?.filter((a) => a.armed && a.selected).length ?? 0;
  const flat = rules.data?.rules.internal.auto_flatten;
  const left = flat ? secondsToEt(flat, now) : null;
  const chip = "rounded-full border border-gold/50 px-2.5 py-0.5 text-xs font-semibold text-gold hover:text-goldLight";

  return (
    <>
      {auto.data && (
        <Link to="/automation" data-testid="automation-mode" title="Automation mode" className={chip}>
          Automation {modeLabel(auto.data.mode)}
        </Link>
      )}
      {ev.data && (
        <Link to="/risk" data-testid="eval-mode" title="Evaluation Mode (change on the Risk page)" className={chip}>
          EVAL MODE {ev.data.enabled ? "ON" : "OFF"}
        </Link>
      )}
      {list && (
        <Link to="/automation" data-testid="trading-count" className="text-xs text-blueLight">
          Trading <b className="text-gold">{trading} of {list.length}</b>
        </Link>
      )}
      {left !== null && (
        <span data-testid="flatten-countdown" className="text-xs text-blueLight" title={`Auto-flatten ${flat} ET`}>
          {left > 0 ? <>Flatten in <b className="font-mono text-gold">{fmtCountdown(left)}</b></> : <>Flatten {flat} ET passed</>}
        </span>
      )}
      <button onClick={() => setOpen((o) => !o)} aria-expanded={open}
        className="rounded border-2 border-gold px-2 py-1 text-xs font-bold text-gold hover:text-goldLight">KILL SWITCH</button>
      {open && (
        <form role="dialog" aria-label="Kill switch" className="flex w-full flex-wrap items-center gap-2 rounded border border-gold p-2 text-xs"
          onSubmit={(e) => { e.preventDefault(); kill.mutate(); }}>
          <span>Flattens everything, turns automation OFF and blocks entries. Type <b className="text-gold">{KILL_PHRASE}</b> to confirm.</span>
          <input aria-label="Kill switch confirmation" value={typed} onChange={(e) => setTyped(e.target.value)}
            className="rounded border border-border bg-bg px-2 py-1 text-blueLight" autoFocus />
          <button type="submit" disabled={typed !== KILL_PHRASE || kill.isPending}
            className="rounded border border-gold px-2 py-1 font-bold text-gold disabled:opacity-40">Confirm kill</button>
          {err && <span role="alert" className="text-goldLight">⚠ {err}</span>}
        </form>
      )}
    </>
  );
}
