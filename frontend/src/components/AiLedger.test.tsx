import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AiLedger, { type AiLedgerResp } from "./AiLedger";

const resp: AiLedgerResp = {
  session: "2026-11-10", symbol: "MNQ", schedule: "02:40",
  live: { stats: { n: 12, hit_rate: 0.75, brier: 0.22, wilson_lb: 0.52 }, state: "UNPROVEN", badge: "ADVISORY", required_accuracy: 0.7, min_calls: 30, calls_needed: { at_current_rate: null, best_case: 14 } },
  backfill_estimate: { stats: { n: 40, hit_rate: 0.8, brier: 0.2, wilson_lb: 0.7 }, label: "x" },
  coverage: [{ day: "2026-11-09", ta: true, vt: false, scored: true }, { day: "2026-11-06", ta: true, vt: true, scored: true }],
  job: { status: "stopped_on_error", total: 10, done: 3, failed: 3, skipped: 0, current: null, provider: "qwen", error: "2026-10-02: timeout" },
  preview: { days: 60, tool_runs: 120, provider: "qwen", est_usd: 21, est_minutes: 120, configured: true, with_vt: true, note: "rough" },
};

test("shows live record apart from the backfill estimate, gaps, progress, error and starts a backfill", async () => {
  const calls: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    calls.push(`${init?.method ?? "GET"} ${String(url)} ${init?.body ? String(init.body) : ""}`);
    return new Response(JSON.stringify(String(url).includes("/preview") ? resp.preview : String(url) === "/api/ai-ledger" ? resp : {}));
  });
  render(<QueryClientProvider client={new QueryClient()}><AiLedger /></QueryClientProvider>);
  expect(await screen.findByTestId("live-record")).toHaveTextContent("12 scored calls");
  expect(screen.getByTestId("calls-needed")).toHaveTextContent("not reachable");
  expect(screen.getByTestId("calls-needed")).toHaveTextContent("at least 14");
  expect(screen.getByTestId("coverage-gaps")).toHaveTextContent("11-09 (no VT)");
  expect(screen.getByTestId("bf-estimate")).toHaveTextContent("estimated accuracy 80%");
  expect(screen.getByText(/does NOT count toward the proof/)).toBeInTheDocument();
  expect(screen.getByTestId("bf-progress")).toHaveTextContent("3/10");
  expect(screen.getByTestId("bf-error")).toHaveTextContent("timeout");
  expect(await screen.findByTestId("bf-cost")).toHaveTextContent("120 tool runs");
  await userEvent.click(screen.getByRole("button", { name: "Start backfill" }));
  expect(calls.some((c) => c.startsWith("POST /api/ai-ledger/backfill") && c.includes('"days":60'))).toBe(true);
});
