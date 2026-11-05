// §18 — font colors ONLY blue/gold. Red/green only as small badges/icons.
export const theme = {
  gold: "#D4AF37",
  goldLight: "#F2D27A",
  blue: "#3B82F6",
  blueLight: "#93C5FD",
  bg: "#0A1020",
  card: "#111A33",
  border: "#1E2A4A",
} as const;

export const badge = { ok: "#22C55E", bad: "#EF4444" } as const; // icons only, never text

function lum(hex: string): number {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const l = c.map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * l[0]! + 0.7152 * l[1]! + 0.0722 * l[2]!;
}

export function contrast(a: string, b: string): number {
  const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p) as [number, number];
  return (x + 0.05) / (y + 0.05);
}
