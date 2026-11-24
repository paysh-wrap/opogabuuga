// Luxe interactions, delegated (one listener each, no per-component wiring):
// pointer-follow sheen vars on cards, and a gold flash on numeric text that changes. Off under reduced motion.
const CARD = "section.bg-card, article.bg-card";
const NUM = ".tabular-nums, .font-mono";

export function installLuxe(doc: Document = document): () => void {
  const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  if (reduce) return () => undefined;
  let raf = 0;
  const onMove = (e: PointerEvent) => {
    const card = (e.target as Element | null)?.closest?.(CARD) as HTMLElement | null;
    if (!card || raf) return;
    raf = requestAnimationFrame(() => {
      raf = 0;
      const r = card.getBoundingClientRect();
      card.style.setProperty("--lx-x", `${e.clientX - r.left}px`);
      card.style.setProperty("--lx-y", `${e.clientY - r.top}px`);
    });
  };
  doc.addEventListener("pointermove", onMove, { passive: true });
  const mo = new MutationObserver((muts) => {
    for (const m of muts) {
      if (m.type !== "characterData") continue;
      const el = m.target.parentElement?.closest(NUM) as HTMLElement | null;
      if (!el || m.oldValue === m.target.textContent) continue;
      el.classList.remove("lx-flash");
      void el.offsetWidth;
      el.classList.add("lx-flash");
    }
  });
  mo.observe(doc.body, { subtree: true, characterData: true, characterDataOldValue: true });
  doc.addEventListener("animationend", (e) => (e.target as Element).classList?.remove("lx-flash"));
  return () => { doc.removeEventListener("pointermove", onMove); mo.disconnect(); };
}
