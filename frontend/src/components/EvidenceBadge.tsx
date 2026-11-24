/** ONE evidence badge per strategy / option. The words come from the API (`badge`, else `status`; unverified is always
 *  labelled UNVERIFIED) — never hard-coded per card. Gold pill = unverified, blue = verified (no red/green text). */
export default function EvidenceBadge({ verified, text, testId }: { verified: boolean; text?: string | null; testId?: string }) {
  const label = verified ? (text || "VERIFIED") : (text && /unverified/i.test(text) ? text : text ? `UNVERIFIED · ${text}` : "UNVERIFIED");
  return (
    <span data-testid={testId} data-verified={verified} className={`rounded border px-1 text-xs font-semibold ${verified ? "border-blue text-blue" : "border-gold text-gold"}`}>
      {label}
    </span>
  );
}
