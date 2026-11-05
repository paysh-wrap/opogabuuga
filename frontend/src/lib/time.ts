// All user-facing times are shown in America/New_York (spec §2).
const tz = "America/New_York";
export const etTime = (iso: string) =>
  new Intl.DateTimeFormat("en-US", { timeZone: tz, hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false })
    .format(new Date(iso)) + " ET";
export const etDateTime = (iso: string) =>
  new Intl.DateTimeFormat("en-US", { timeZone: tz, month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
    hour12: false }).format(new Date(iso)) + " ET";
