// D80: projections assume the hindsight fade rule (D77 finding). Informational only; no numbers are changed.
export default function HindsightNote() {
  return (
    <p className="rounded-lg border border-gold px-3 py-2 text-xs text-blue" data-testid="hindsight-note">
      <b className="text-gold">Projection notice:</b> income and pass projections assume the fade rule that uses the whole day (hindsight, D77). A causal version is about 25% less profit with about 10 points more bust risk, so treat projections as optimistic until you decide on the rebuild.
    </p>
  );
}
