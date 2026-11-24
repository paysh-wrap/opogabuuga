// Sliding gold underline under the active nav item (one absolutely-positioned element, transform only). Off under reduced motion.
export function installFancy(doc: Document = document): () => void {
  const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  let ink: HTMLElement | null = null;
  const place = () => {
    const nav = doc.querySelector<HTMLElement>('nav[aria-label="Main"]');
    const a = nav?.querySelector<HTMLElement>("a.text-gold, a[aria-current='page']");
    if (!nav || !a || nav.offsetParent === null) { ink?.style.setProperty("opacity", "0"); return; }
    if (!ink || !nav.contains(ink)) { ink = doc.createElement("span"); ink.className = "nav-ink"; ink.setAttribute("aria-hidden", "true"); nav.appendChild(ink); }
    const n = nav.getBoundingClientRect(), r = a.getBoundingClientRect();
    ink.style.opacity = "1";
    ink.style.width = `${r.width}px`;
    ink.style.transform = `translate(${r.left - n.left}px, ${r.bottom - n.top - 2}px)`;
  };
  let raf = 0;
  const sched = () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(place); };
  const mo = new MutationObserver(sched);
  mo.observe(doc.body, { subtree: true, attributes: true, attributeFilter: ["class", "aria-current"], childList: true });
  window.addEventListener("resize", sched);
  sched();
  // 3D tilt (max 3deg) on stat tiles + magnetic primary buttons; pointer devices only, never under reduced motion.
  const fine = window.matchMedia?.("(hover: hover) and (pointer: fine)").matches;
  const onMove = (e: PointerEvent) => {
    const t = e.target as Element | null;
    const tile = t?.closest?.<HTMLElement>(".mission-bento > *, .mission main .tile");
    const btn = t?.closest?.<HTMLElement>("main button.bg-gold:not(:disabled), main button.bg-blue:not(:disabled)");
    for (const el of doc.querySelectorAll<HTMLElement>("[data-fx-tilt],[data-fx-mag]")) if (el !== tile && el !== btn) { el.style.transform = ""; el.removeAttribute("data-fx-tilt"); el.removeAttribute("data-fx-mag"); }
    if (tile) { const r = tile.getBoundingClientRect(); const x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
      tile.setAttribute("data-fx-tilt", ""); tile.style.transform = `perspective(900px) rotateX(${(-y * 6).toFixed(2)}deg) rotateY(${(x * 6).toFixed(2)}deg)`; }
    if (btn) { const r = btn.getBoundingClientRect(); const x = e.clientX - r.left - r.width / 2, y = e.clientY - r.top - r.height / 2;
      btn.setAttribute("data-fx-mag", ""); btn.style.transform = `translate(${(x * 0.12).toFixed(1)}px, ${(y * 0.2).toFixed(1)}px)`; }
  };
  const motion = fine && !reduce;
  if (motion) doc.addEventListener("pointermove", onMove, { passive: true });
  return () => { mo.disconnect(); window.removeEventListener("resize", sched); if (motion) doc.removeEventListener("pointermove", onMove); ink?.remove(); };
}
