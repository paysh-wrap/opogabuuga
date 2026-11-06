import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { browserNotifyEnabled, disableBrowserNotify, enableBrowserNotify, notifySupported } from "../lib/notify";
import { Link } from "react-router-dom";
import { api, type Health } from "../lib/api";
import { usePageTitle } from "../components/usePageTitle";

interface Rules {
  rules: {
    schedule: Record<string, string | string[] | number>;
    automation: {
      default_mode: string;
      accounts_to_trade: number;
      selection_mode: string;
      semi_auto_sessions_per_stage: number;
      require_external_attestation: boolean;
      auto_resume_after_recovery: { paper: boolean; live: boolean };
    };
    score?: { weights: Record<string, number | string>; min_score: number | string; neutral_min_score: number | string; osc_strength_min: number | string };
  };
  verify_paths: string[];
}
interface Conn { id: string; name: string; status: string; required: boolean }
interface Gate {
  run_id: number | null;
  passed: boolean;
  unmeasured: string[];
  checks: { key: string; label: string; need: string; value: string | null; ok: boolean | null }[];
}

const card = "rounded-xl border border-border bg-card p-4";

function Section({ title, children, loading, error }: { title: string; children: React.ReactNode; loading: boolean; error: boolean }) {
  return (
    <section className={card}>
      <h2 className="font-semibold text-gold">{title}</h2>
      {loading && <p role="status" className="mt-1 text-sm">Loading…</p>}
      {error && <p role="alert" className="mt-1 text-sm text-goldLight">⚠ Could not load this section.</p>}
      {!loading && !error && children}
    </section>
  );
}

function BrowserNotifications() {
  const [on, setOn] = useState(browserNotifyEnabled);
  const [msg, setMsg] = useState("");
  async function toggle() {
    if (on) {
      disableBrowserNotify();
      setOn(false);
      setMsg("Browser notifications off.");
      return;
    }
    const p = await enableBrowserNotify();
    setOn(p === "granted");
    setMsg(p === "granted" ? "Browser notifications on." : p === "unsupported" ? "This browser has no notifications." : "Permission not granted by the browser.");
  }
  return (
    <section className={card}>
      <h2 className="font-semibold text-gold">Notifications</h2>
      <p className="mt-1 text-sm">Alerts (kill switch, pauses, risk alerts, payout ready, pre-flight failures, inactivity) are always listed under the 🔔 in the header.
        Optionally also show them as browser notifications while Paytience is open — nothing is sent to any outside service.</p>
      <button data-testid="browser-notify" onClick={() => void toggle()} disabled={!notifySupported()}
        className="mt-2 rounded-md border border-blue px-3 py-1.5 text-sm font-semibold text-blue disabled:opacity-50">
        {on ? "Turn off browser notifications" : "Turn on browser notifications"}
      </button>
      {msg && <p role="status" className="mt-1 text-xs">{msg}</p>}
    </section>
  );
}

export default function Settings() {
  usePageTitle("Settings");
  const health = useQuery({ queryKey: ["health"], queryFn: () => api<Health>("/api/health") });
  const auto = useQuery({ queryKey: ["automation"], queryFn: () => api<{ mode: string }>("/api/automation") });
  const rules = useQuery({ queryKey: ["rules"], queryFn: () => api<Rules>("/api/rules") });
  const conns = useQuery({ queryKey: ["connections"], queryFn: () => api<{ connections: Conn[] }>("/api/connections") });
  const gate = useQuery({ queryKey: ["gate"], queryFn: () => api<Gate>("/api/gate/purchase") });
  const r = rules.data?.rules;

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-gold">Settings</h1>
      <p className="text-sm">Read-only summary. Change values on the <Link to="/risk" className="text-blue underline">Risk</Link>, <Link to="/automation" className="text-blue underline">Automation</Link> and <Link to="/connections" className="text-blue underline">Connections</Link> pages.</p>

      <Section title="Mode" loading={health.isLoading || auto.isLoading} error={!!(health.error || auto.error)}>
        <p data-testid="settings-mode" className="mt-1 text-sm">
          Trading mode <b className="text-gold">{health.data?.mode}</b> · Automation <b className="text-gold">{auto.data?.mode}</b>
          {r && <> · default {r.automation.default_mode} · first {r.automation.semi_auto_sessions_per_stage} sessions per stage OFF/SEMI only</>}
        </p>
      </Section>

      <Section title="Schedule (ET)" loading={rules.isLoading} error={!!rules.error}>
        <dl data-testid="settings-schedule" className="mt-2 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
          {r && Object.entries(r.schedule).map(([k, v]) => (
            <div key={k} className="flex justify-between border-b border-border/50"><dt>{k.replace(/_/g, " ")}</dt><dd className="font-mono text-gold">{Array.isArray(v) ? v.join(", ") : String(v)}</dd></div>
          ))}
        </dl>
        {r && (
          <p className="mt-2 text-xs">Auto-resume after recovery: paper {r.automation.auto_resume_after_recovery.paper ? "yes" : "no"}, live {r.automation.auto_resume_after_recovery.live ? "yes" : "no"} ·
            attestation {r.automation.require_external_attestation ? "required" : "not required"} · up to {r.automation.accounts_to_trade} accounts.</p>
        )}
      </Section>

      <Section title="Score weights" loading={rules.isLoading} error={!!rules.error}>
        {r?.score && (() => {
          const w = Object.entries(r.score.weights).map(([k, v]) => [k, Number(v)] as const);
          const total = w.reduce((s, [, v]) => s + v, 0) || 1;
          return (
            <>
              <table data-testid="settings-weights" className="mt-2 w-full text-sm"><tbody>
                {w.map(([k, v]) => (
                  <tr key={k} className="border-t border-border">
                    <td className="py-1">{k.replace(/_/g, " ")}</td><td className="text-right font-mono text-gold">{v}</td>
                    <td className="w-1/3 pl-3"><div className="h-1.5 rounded bg-border"><div className="h-1.5 rounded bg-blue" style={{ width: `${Math.round((v / total) * 100)}%` }} /></div></td>
                  </tr>
                ))}
              </tbody></table>
              <p className="mt-2 text-xs">Score decides position size only (never whether a gate passes). Minimum score {String(r.score.min_score)} · neutral-bias minimum {String(r.score.neutral_min_score)} · oscillator strength ≥ {String(r.score.osc_strength_min)}.
                Weights are tuned only by the Strategy Lab, within 50–150% each (§17.2).</p>
            </>
          );
        })()}
      </Section>

      <BrowserNotifications />

      <Section title="Notification &amp; data connections" loading={conns.isLoading} error={!!conns.error}>
        <ul data-testid="settings-connections" className="mt-2 grid gap-1 text-sm sm:grid-cols-2">
          {conns.data?.connections.filter((c) => c.status !== "link").map((c) => (
            <li key={c.id} className="flex justify-between border-b border-border/50"><span>{c.name}{c.required ? " *" : ""}</span><span className="text-gold">{c.status.replace(/_/g, " ")}</span></li>
          ))}
        </ul>
        <p className="mt-2 text-xs">* required. Manage on <Link to="/connections" className="text-blue underline">Connections</Link>.
          {rules.data && rules.data.verify_paths.length > 0 && ` ${rules.data.verify_paths.length} firm rule value(s) still marked VERIFY.`}</p>
      </Section>

      <Section title="Evaluation purchase gate (§16.9)" loading={gate.isLoading} error={!!gate.error}>
        <p data-testid="gate-status" className="mt-1 text-sm">
          {gate.data?.passed ? "Gate passed." : "Not passed yet — do not buy evaluations."}
          {gate.data?.run_id === null && " No finished backtest run yet."}
        </p>
        <table className="mt-2 w-full text-sm"><tbody>
          {gate.data?.checks.map((c) => (
            <tr key={c.key} data-testid={`gate-${c.key}`} className="border-t border-border">
              <td className="py-1">{c.label}</td><td>{c.need}</td><td className="text-gold">{c.value ?? "—"}</td>
              <td className="text-right">{c.ok === null ? "not tracked" : c.ok ? "✓ met" : "✗ not met"}</td>
            </tr>
          ))}
        </tbody></table>
      </Section>
    </div>
  );
}
