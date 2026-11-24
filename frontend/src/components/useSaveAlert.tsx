import { useState } from "react";

/** Shared "no silent failures" state for Strategy-page saves: a failed PUT /api/risk/settings shows a role=alert with the
 *  server's reason (D167 / validation / network); a later success clears it. */
export function useSaveAlert() {
  const [error, setError] = useState<string | null>(null);
  return {
    error,
    ok: () => setError(null),
    fail: (what: string, e: unknown) => setError(`${what} not saved: ${e instanceof Error && e.message ? e.message : "unknown error"}`),
  };
}

export function SaveAlert({ error, testId = "save-error" }: { error: string | null; testId?: string }) {
  if (!error) return null;
  return <p role="alert" className="mt-2 rounded border border-gold p-2 text-sm text-goldLight" data-testid={testId}>⚠ {error}</p>;
}
