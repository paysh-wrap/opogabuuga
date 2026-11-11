import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { hardReload, isStaleUi, short, UI_COMMIT, type BuildHealth } from "../lib/build";

function useBuild() {
  return useQuery({
    queryKey: ["build-health"],
    queryFn: () => api<BuildHealth>("/api/health"),
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
    retry: false,
  });
}

/** D97: shown when this page's UI build differs from the server build (old cached interface or old server). */
export function StaleUiBanner() {
  const { data } = useBuild();
  const server = data?.build?.commit;
  if (!isStaleUi(UI_COMMIT, server)) return null;
  return (
    <div role="alert" data-testid="banner-stale-ui" className="sticky top-0 z-50 border-b-2 border-gold bg-card px-4 py-3 text-center text-sm font-semibold text-goldLight">
      ⚠ You are looking at the OLD interface (UI {short(UI_COMMIT)}, server {short(server)}) —{" "}
      <button className="rounded-md border border-gold px-3 py-1 text-gold" onClick={() => void hardReload()}>
        Reload
      </button>
    </div>
  );
}

/** D97: always-visible one-liner so you can tell WHICH server and UI you are looking at. */
export function BuildFooter() {
  const { data, isError } = useBuild();
  const started = data?.started_at ? new Date(data.started_at).toLocaleString() : "?";
  return (
    <footer data-testid="build-footer" className="px-4 pb-24 pt-2 text-center text-xs text-blue md:pb-3">
      {isError
        ? `Server: not reachable · UI ${short(UI_COMMIT)}`
        : `Server: ${data?.executable ?? "?"} · build ${short(data?.build?.commit)} · started ${started} · UI ${short(UI_COMMIT)}`}
    </footer>
  );
}
