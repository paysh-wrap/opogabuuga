// D80/session 14: projections now use the causal fade rule (D77 follow-up, rebuilt 2026-11-10). Informational only.
export default function HindsightNote() {
  return (
    <p className="rounded-lg border border-gold px-3 py-2 text-xs text-blue" data-testid="hindsight-note">
      <b className="text-gold">Projection notice (numbers dated 2026-11-10):</b> income and pass projections are causal: the afternoon fade only trades if NOISE has not already fired that day, exactly as the live app does. Earlier numbers used the whole day (hindsight) and were about 27% too high.
    </p>
  );
}
