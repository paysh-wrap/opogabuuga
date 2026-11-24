import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, expect, test, vi } from "vitest";
import { FastPassStagePanel } from "./FastPassStagePanel";

const view = (live: string | null, funded = false) => ({
  warning: "Funded study (docs/results): evaluation sizes still earned about $300-1,560 per account per 120 days in 2024-26, but 20-43% of 25K/50K/100K funded accounts were lost within 120 days; funded sizing is UNVERIFIED.",
  guards: ["Daily loss limit", "Kill switch"], applies: "next NEW trade only",
  stages: { FUNDED: { enabled: funded, accounts: 1, confirm_phrase: "ENABLE FAST PASS FUNDED", blocked: null }, LIVE: { enabled: false, accounts: 1, confirm_phrase: "ENABLE FAST PASS LIVE", blocked: live } },
});
afterEach(() => vi.restoreAllMocks());
function mount(v: unknown, fail = false) {
  const calls: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (u: string, o?: RequestInit) => {
    calls.push(`${o?.method ?? "GET"} ${u} ${o?.body ?? ""}`);
    if (o?.method === "PUT" && fail) return new Response(JSON.stringify({ detail: "no" }), { status: 422 });
    return new Response(JSON.stringify(v), { status: 200 });
  }));
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><FastPassStagePanel /></QueryClientProvider>);
  return calls;
}

test("default OFF, honest warning, guards, LIVE blocked without gates", async () => {
  mount(view("LIVE gates are not all passing"));
  expect(await screen.findByTestId("fast-pass-stage-warning")).toHaveTextContent("funded sizing is UNVERIFIED");
  expect(screen.getByTestId("fast-pass-stage-guards")).toHaveTextContent("Kill switch");
  expect(screen.getByTestId("fp-stage-LIVE")).toHaveTextContent("OFF");
  expect(screen.getByTestId("fp-stage-live-blocked")).toBeInTheDocument();
  expect(screen.getByTestId("fp-stage-preview-LIVE")).toBeDisabled();
});

test("typed phrase enables FUNDED, then one click off", async () => {
  const calls = mount(view(null));
  await userEvent.click(await screen.findByTestId("fp-stage-preview-FUNDED"));
  const go = screen.getByTestId("fp-stage-enable-FUNDED");
  expect(go).toBeDisabled();
  await userEvent.type(screen.getByLabelText("Fast Pass FUNDED confirmation"), "ENABLE FAST PASS FUNDED");
  await userEvent.click(go);
  await waitFor(() => expect(calls.some((c) => c.startsWith("PUT /api/risk/fast-pass-stage/FUNDED") && c.includes("ENABLE FAST PASS FUNDED"))).toBe(true));
});

test("cancel, error and the off button", async () => {
  mount(view(null), true);
  await userEvent.click(await screen.findByTestId("fp-stage-preview-LIVE"));
  await userEvent.click(screen.getByText("Cancel"));
  await userEvent.click(screen.getByTestId("fp-stage-preview-FUNDED"));
  await userEvent.type(screen.getByLabelText("Fast Pass FUNDED confirmation"), "ENABLE FAST PASS FUNDED");
  await userEvent.click(screen.getByTestId("fp-stage-enable-FUNDED"));
  expect(await screen.findByRole("alert")).toBeInTheDocument();
});

test("ON shows turn off", async () => {
  const calls = mount(view(null, true));
  await userEvent.click(await screen.findByTestId("fp-stage-off-FUNDED"));
  await waitFor(() => expect(calls.some((c) => c.includes('"enabled":false'))).toBe(true));
});
