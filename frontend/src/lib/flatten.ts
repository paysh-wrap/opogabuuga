// Seconds until the next "HH:MM" Eastern wall-clock time today (negative once passed). Pure; `now` injected.
export function secondsToEt(hhmm: string, now: Date): number {
  const [h, m] = hhmm.split(":").map(Number);
  const p = new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", hour: "2-digit", minute: "2-digit",
    second: "2-digit", hour12: false }).formatToParts(now);
  const g = (t: string) => Number(p.find((x) => x.type === t)?.value ?? 0) % 24;
  return (h! * 3600 + m! * 60) - (g("hour") * 3600 + g("minute") * 60 + g("second"));
}

export function fmtCountdown(sec: number): string {
  const s = Math.max(0, sec);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(Math.floor(s / 3600))}:${pad(Math.floor((s % 3600) / 60))}:${pad(s % 60)}`;
}
