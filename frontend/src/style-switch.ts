// Style variant switch: ?style=glass|terminal|neon|minimal (or localStorage "paytience.style"). Unknown/empty = current look.
const STYLES = ["glass", "terminal", "neon", "minimal"] as const;
type StyleName = (typeof STYLES)[number];
const KEY = "paytience.style";
const ok = (v: string | null): v is StyleName => !!v && (STYLES as readonly string[]).includes(v);

export function applyStyle(): void {
  let chosen: string | null = null;
  try {
    const q = new URLSearchParams(window.location.search).get("style");
    if (q !== null) {
      if (ok(q)) window.localStorage.setItem(KEY, q);
      else window.localStorage.removeItem(KEY); // ?style=default (or anything else) resets
      chosen = q;
    } else chosen = window.localStorage.getItem(KEY);
  } catch { /* storage blocked: URL/default only */ }
  if (ok(chosen)) document.documentElement.dataset.style = chosen;
  else delete document.documentElement.dataset.style;
}
