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
  // magnetic primary buttons: follow the pointer by at most 3px
  const onBtn = (e: PointerEvent) => {
    const b = (e.target as Element | null)?.closest?.("main button.border-gold:not(:disabled)") as HTMLElement | null;
    if (!b) return;
    const r = b.getBoundingClientRect();
    b.style.setProperty("--lx-mx", `${(((e.clientX - r.left) / r.width) - 0.5) * 6}px`);
    b.style.setProperty("--lx-my", `${(((e.clientY - r.top) / r.height) - 0.5) * 6}px`);
  };
  const offBtn = (e: PointerEvent) => {
    const b = e.target as HTMLElement;
    if (b?.matches?.("button.border-gold")) { b.style.removeProperty("--lx-mx"); b.style.removeProperty("--lx-my"); }
  };
  doc.addEventListener("pointermove", onBtn, { passive: true });
  doc.addEventListener("pointerout", offBtn, { passive: true });
  const mo = new MutationObserver((muts) => {
    for (const m of muts) {
      if (m.type === "childList") {
        // pulse table rows added after first paint (new data)
        m.addedNodes.forEach((n) => { if (n instanceof HTMLTableRowElement && n.parentElement?.tagName === "TBODY") n.classList.add("lx-new"); });
        continue;
      }
      if (m.type !== "characterData") continue;
      const el = m.target.parentElement?.closest(NUM) as HTMLElement | null;
      if (!el || m.oldValue === m.target.textContent) continue;
      el.classList.remove("lx-flash");
      void el.offsetWidth;
      el.classList.add("lx-flash");
    }
  });
  mo.observe(doc.body, { subtree: true, characterData: true, characterDataOldValue: true, childList: true });
  doc.addEventListener("animationend", (e) => (e.target as Element).classList?.remove("lx-flash", "lx-new"));
  return () => { doc.removeEventListener("pointermove", onMove); doc.removeEventListener("pointermove", onBtn); doc.removeEventListener("pointerout", offBtn); mo.disconnect(); };
}
