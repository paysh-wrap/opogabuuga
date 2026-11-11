/** D97: compare the UI build commit with the server's, so an OLD interface is never mistaken for the new one. */

export const UI_COMMIT: string = typeof __UI_COMMIT__ === "string" ? __UI_COMMIT__ : "dev";

export interface BuildHealth {
  app: string;
  build?: { commit: string; built_at: string };
  started_at?: string;
  executable?: string;
}

export const short = (c: string | undefined): string => (c ? c.slice(0, 7) : "?");

const known = (c: string | undefined): c is string => !!c && c !== "dev";

/** True when both commits are known and differ (prefix compare: short and full SHAs both work). */
export function isStaleUi(ui: string, server: string | undefined): boolean {
  if (!known(ui) || !known(server)) return false;
  const a = ui.toLowerCase();
  const b = server.toLowerCase();
  return !(a.startsWith(b) || b.startsWith(a));
}

/** Hard reload: a changing query string bypasses any cached index.html / service-worker shell. */
export async function hardReload(): Promise<void> {
  try {
    if ("serviceWorker" in navigator) {
      const regs = await navigator.serviceWorker.getRegistrations();
      await Promise.all(regs.map((r) => r.unregister()));
    }
    if (typeof caches !== "undefined") {
      const keys = await caches.keys();
      await Promise.all(keys.map((k) => caches.delete(k)));
    }
  } catch {
    /* best effort: the cache-busting URL below is what matters */
  }
  const u = new URL(window.location.href);
  u.searchParams.set("reload", String(Date.now()));
  window.location.replace(u.toString());
}
