import { useEffect, useRef, useState } from "react";

/** Eases a number from its previous value to `target` (~600 ms). Returns target immediately under reduced motion / first render. */
export function useCountUp(target: number, ms = 600): number {
  const [v, setV] = useState(target);
  const from = useRef(target);
  useEffect(() => {
    const start = from.current;
    const reduce = typeof window === "undefined" || !window.matchMedia || window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce || start === target || !Number.isFinite(target)) { from.current = target; setV(target); return; }
    let raf = 0; const t0 = performance.now();
    const step = (t: number) => {
      const k = Math.min(1, (t - t0) / ms); const e = 1 - Math.pow(1 - k, 3);
      const cur = start + (target - start) * e; from.current = cur; setV(k < 1 ? cur : target);
      if (k < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target, ms]);
  return v;
}
