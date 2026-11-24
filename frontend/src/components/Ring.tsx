import { theme, mission } from "../lib/theme";

/** Tiny pure-SVG progress ring (gold on navy). Hidden by callers when there is no data. Decorative: text next to it carries the value. */
export function Ring({ pct, size = 44, label }: { pct: number; size?: number; label: string }) {
  if (!Number.isFinite(pct)) return null;
  const p = Math.max(0, Math.min(100, pct));
  const r = 18;
  return (
    <svg className="lx-ring" width={size} height={size} viewBox="0 0 44 44" role="img" aria-label={`${label} ${Math.round(p)}%`}>
      <circle cx="22" cy="22" r={r} fill="none" stroke={mission.navOn} strokeWidth="5" />
      <circle cx="22" cy="22" r={r} fill="none" stroke={theme.gold} strokeWidth="5" strokeLinecap="round" pathLength={100}
        strokeDasharray={`${p} 100`} transform="rotate(-90 22 22)" />
      <text x="22" y="25.5" textAnchor="middle" fontSize="10" fontWeight="700" fill={theme.goldLight}>{Math.round(p)}</text>
    </svg>
  );
}

/** Optional sparkline from an existing series; renders nothing under 2 points. */
export function Spark({ data, label }: { data: number[]; label: string }) {
  const d = data.filter(Number.isFinite);
  if (d.length < 2) return null;
  const lo = Math.min(...d), hi = Math.max(...d), span = hi - lo || 1;
  const pts = d.map((v, i) => `${(i / (d.length - 1)) * 100},${28 - ((v - lo) / span) * 24}`);
  return (
    <svg className="lx-spark" viewBox="0 0 100 30" preserveAspectRatio="none" role="img" aria-label={label} width="100%" height="30">
      <polygon points={`0,30 ${pts.join(" ")} 100,30`} fill={theme.blue} opacity=".14" />
      <polyline points={pts.join(" ")} fill="none" stroke={theme.blueLight} strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}
