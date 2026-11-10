import { useState } from "react";

const field = "w-20";

/** Risk page control for the feed-loss protection (reliability.* in My Settings; validated server-side). */
export default function FeedGuardSettings({ settings, save }: { settings: Record<string, unknown>; save: (c: Record<string, unknown>) => void }) {
  const on = settings["reliability.feed_guard_enabled"] !== false;
  const [warn, setWarn] = useState(String(settings["reliability.feed_warn_min"] ?? 3));
  const [flat, setFlat] = useState(String(settings["reliability.feed_flatten_min"] ?? 6));
  const w = Number(warn), f = Number(flat);
  const valid = Number.isInteger(w) && Number.isInteger(f) && w >= 1 && f > w;
  return (
    <section className="rounded-xl border border-border bg-card p-4" data-testid="feed-guard">
      <h2 className="font-semibold text-gold">Price-feed protection {on ? "· ON" : "· OFF"}</h2>
      <p className="text-xs">
        If a position is open and no 1-minute price bar arrives (dead tunnel or a stopped TradingView alert), the app warns and blocks new entries,
        then closes the position by itself. The broker's own stop and target stay in place.
      </p>
      <label className="mt-2 flex items-center gap-2 text-sm">
        <input type="checkbox" data-testid="feed-guard-on" checked={on} onChange={(e) => save({ "reliability.feed_guard_enabled": e.target.checked })} />
        Protect open positions when price bars stop
      </label>
      <div className="mt-2 flex flex-wrap items-center gap-3 text-sm">
        <label>Warn and block entries after <input aria-label="Warn after minutes" className={field} value={warn} onChange={(e) => setWarn(e.target.value)} /> min</label>
        <label>Close the position after <input aria-label="Flatten after minutes" className={field} value={flat} onChange={(e) => setFlat(e.target.value)} /> min</label>
        <button data-testid="feed-guard-save" disabled={!valid} className="rounded-md border border-gold px-3 py-1.5 text-sm font-semibold text-gold disabled:opacity-50"
          onClick={() => save({ "reliability.feed_warn_min": w, "reliability.feed_flatten_min": f })}>Save</button>
      </div>
      {!valid && <p role="alert" className="mt-1 text-xs text-goldLight">⚠ Close-after must be larger than warn-after (whole minutes).</p>}
    </section>
  );
}
