// B7 / D135 (session 20): projections re-based on the session-19 shipped config (NOISE profit lock + Mondays off, causal
// afternoon fade with Mondays off). Informational only.
export default function HindsightNote() {
  return (
    <p className="rounded-lg border border-gold px-3 py-2 text-xs text-blue" data-testid="hindsight-note">
      <b className="text-gold">Projection notice (numbers dated 2026-11-12):</b> income projections replay the shipped MAIN strategy on 7.5 years of real MNQ data (2019-05 → 2026-11): NOISE with the profit lock (+100 pt → stop to entry +10), Mondays off, and the afternoon fade only on days NOISE did not trade (Mondays off too), exactly as the live app trades a funded account. Research replay, not a promise.
    </p>
  );
}
