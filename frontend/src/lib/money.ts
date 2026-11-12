// B8 (session 20): one money format: whole dollars without cents, otherwise always 2 decimals ("$437.50", not "$437.5").
export function money(v?: string | number | null): string {
  if (v == null || v === "") return "—";
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  const cents = Math.round(Math.abs(n) * 100) % 100 !== 0;
  const s = Math.abs(n).toLocaleString(undefined, cents ? { minimumFractionDigits: 2, maximumFractionDigits: 2 } : { maximumFractionDigits: 0 });
  return `${n < 0 ? "-" : ""}$${s}`;
}
