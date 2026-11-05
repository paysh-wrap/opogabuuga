import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { usePageTitle } from "../components/usePageTitle";

export default function Login() {
  usePageTitle("Login");
  const nav = useNavigate();
  const qc = useQueryClient();
  const [username, setU] = useState("PayDay");
  const [password, setP] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      await api("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });
      await qc.invalidateQueries();
      nav("/connections");
    } catch (x) {
      setErr(x instanceof ApiError ? x.message : "Cannot reach server");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-2xl border border-border bg-card p-7 shadow-[0_0_40px_-12px_#D4AF37]">
        <div className="text-center">
          <h1 className="text-3xl font-bold tracking-wide text-gold">Paytience</h1>
          <p className="mt-1 text-sm">Automated confluence trading · Lucid accounts</p>
        </div>
        <label className="block text-sm">Username
          <input className="mt-1 w-full" value={username} onChange={(e) => setU(e.target.value)} autoComplete="username" />
        </label>
        <label className="block text-sm">Password
          <input className="mt-1 w-full" type="password" value={password} onChange={(e) => setP(e.target.value)}
            autoComplete="current-password" autoFocus />
        </label>
        {err && <p role="alert" className="text-sm text-goldLight">⚠ {err}</p>}
        <button disabled={busy || !password} className="w-full rounded-md border border-blue bg-blue/10 py-2 font-semibold text-blue transition-colors hover:bg-blue/20 disabled:opacity-50">
          {busy ? "Signing in…" : "Sign in"}
        </button>
        <p className="text-center text-xs opacity-70">Locks for 1 minute after 5 failed attempts</p>
      </form>
    </div>
  );
}
