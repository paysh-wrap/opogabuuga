import type { ReactNode } from "react";

/** Long study / explanation text folded behind a "More info" button (session 22, item 11). Nothing is removed: the
 *  text stays in the page and opens with one tap. A native <details> keeps it keyboard- and screen-reader-friendly. */
export default function MoreInfo({ children, label = "More info", testId }: { children: ReactNode; label?: string; testId?: string }) {
  return (
    <details className="more-info mt-2 text-xs" data-testid={testId}>
      <summary className="more-info-btn inline-flex cursor-pointer select-none items-center gap-1 rounded-md border border-blue px-2 py-0.5 font-semibold text-blue">
        {label}
      </summary>
      <div className="mt-2">{children}</div>
    </details>
  );
}
