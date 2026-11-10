import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../lib/api";

export interface Safety {
  unmanaged: { account: string; reason: string }[];
  feed: { symbol: string; state: "WARN" | "LOST" }[];
  pending_exits: { signal_id: number; symbol: string; reason: string; since: string | null }[];
  missed_checks: { symbol: string; minute_et: string; key: string }[];
}

const box = "rounded-lg border border-gold bg-card p-3 text-sm text-goldLight";

/** Plain-language safety states (session 14): restart found a position, feed lost, missed NOISE check, exit waiting. */
export default function SafetyBanners() {
  const q = useQuery({ queryKey: ["safety"], queryFn: () => api<Safety>("/api/safety"), refetchInterval: 10_000 });
  const d = q.data;
  if (!d) return null;
  const items: JSX.Element[] = [];
  (d.unmanaged ?? []).forEach((u) =>
    items.push(
      <div key={`u-${u.account}`} role="alert" data-testid="banner-unmanaged" className={box}>
        ⚠ <b className="text-gold">Restart found an unmanaged position</b> on {u.account}.{" "}
        {u.reason === "RESTART_UNVERIFIED"
          ? "The app could not read the broker after restarting, so new entries are blocked on this account until you check it."
          : "Paytience flattened it and paused the account. Check Tradovate, then resume the account on the Accounts page."}{" "}
        <Link className="text-blue underline" to="/accounts">Accounts</Link>
      </div>,
    ),
  );
  (d.feed ?? []).forEach((f) =>
    items.push(
      <div key={`f-${f.symbol}`} role="alert" data-testid={`banner-feed-${f.symbol}`} className={box}>
        ⚠ <b className="text-gold">Price feed lost while in a position</b> ({f.symbol}). No new entries.{" "}
        {f.state === "LOST" ? "The position is being closed (FEED_LOST)." : "It will be closed automatically if bars do not return soon."}{" "}
        Check the TradingView alert and the tunnel on <Link className="text-blue underline" to="/connections">Connections</Link>.
      </div>,
    ),
  );
  (d.missed_checks ?? []).slice(-3).forEach((m) =>
    items.push(
      <div key={m.key} role="alert" data-testid="banner-missed-check" className={box}>
        ⚠ <b className="text-gold">Missed check minute</b> {m.minute_et} ET ({m.symbol}): no price bar arrived, so that NOISE decision was skipped.
      </div>,
    ),
  );
  (d.pending_exits ?? []).forEach((p) =>
    items.push(
      <div key={`p-${p.signal_id}`} role="status" data-testid="banner-exit-pending" className={box}>
        ⏳ <b className="text-gold">Exit pending broker confirmation</b> ({p.symbol}, {p.reason}). The app keeps retrying until the position is really flat.
      </div>,
    ),
  );
  return items.length ? <div className="mb-4 space-y-2" data-testid="safety-banners">{items}</div> : null;
}
