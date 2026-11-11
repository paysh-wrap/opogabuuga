// Style variant switch: ?style=glass|terminal|neon|minimal|royal|classic (or localStorage "paytience.style").
// D124 (user 2026-11-11): Neon is the default look; ?style=classic shows the previous look.
const STYLES = ["glass", "terminal", "neon", "minimal", "royal"] as const;
type StyleName = (typeof STYLES)[number];
const KEY = "paytience.style";
const DEFAULT: StyleName = "neon";
const ok = (v: string | null): v is StyleName => !!v && (STYLES as readonly string[]).includes(v);

export function applyStyle(): void {
  let chosen: string | null = null;
  try {
    const q = new URLSearchParams(window.location.search).get("style");
    if (q !== null) {
      if (ok(q) || q === "classic") window.localStorage.setItem(KEY, q);
      else window.localStorage.removeItem(KEY); // ?style=default (or anything else) resets
      chosen = q;
    } else chosen = window.localStorage.getItem(KEY);
  } catch { /* storage blocked: URL/default only */ }
  if (chosen === "classic") delete document.documentElement.dataset.style;
  else document.documentElement.dataset.style = ok(chosen) ? chosen : DEFAULT;
}
