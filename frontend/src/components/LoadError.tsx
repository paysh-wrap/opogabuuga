/** Failed-load state (no silent failures): says what could not load, why, and offers a retry instead of "Loading…" forever. */
export default function LoadError({ what, error, onRetry, hint }: { what: string; error: unknown; onRetry?: () => void; hint?: string }) {
  const msg = error instanceof Error && error.message ? error.message : "unknown error";
  return (
    <div role="alert" data-testid="load-error" className="rounded-lg border border-gold bg-card p-3 text-sm text-goldLight">
      ⚠ Cannot load {what}: {msg}.{hint ? ` ${hint}` : ""}{" "}
      {onRetry && (
        <button type="button" onClick={onRetry} className="ml-1 rounded-md border border-blue px-2 py-0.5 text-xs font-semibold text-blue">Retry</button>
      )}
    </div>
  );
}
