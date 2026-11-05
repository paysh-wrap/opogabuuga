import type { Status } from "../lib/api";
import { badge } from "../lib/theme";

const LABEL: Record<Status, string> = {
  connected: "Connected",
  saved: "Saved",
  failed: "Failed",
  not_set: "Not set",
  waiting: "Waiting",
  link: "Link only",
};

// Text stays blue/gold (§18); red/green appear only as the small dot.
export default function StatusBadge({ status }: { status: Status }) {
  const dot = status === "connected" ? badge.ok : status === "failed" ? badge.bad : "transparent";
  const text = status === "connected" ? "text-gold" : "text-blueLight";
  return (
    <span data-testid="status" data-status={status}
      className={`inline-flex items-center gap-1.5 rounded-full border border-border px-2 py-0.5 text-xs font-semibold ${text}`}>
      <span aria-hidden className="h-2 w-2 rounded-full border border-border" style={{ background: dot }} />
      {LABEL[status]}
    </span>
  );
}
