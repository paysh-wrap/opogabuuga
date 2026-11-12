import { render, screen, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import MandatoryChecklist from "./MandatoryChecklist";

afterEach(() => vi.restoreAllMocks());

function setup(routes: Record<string, unknown>) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
    const body = routes[String(url)];
    return body === undefined ? new Response("{}", { status: 503 }) : new Response(JSON.stringify(body));
  });
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><MandatoryChecklist /></MemoryRouter>
    </QueryClientProvider>,
  );
}

const connections = {
  connections: [
    { id: "crosstrade", name: "CrossTrade", category: "broker", purpose: "", required: false, testable: true, steps: [], note: "",
      links: [], fields: [], status: "connected", detail: "Key accepted", hints: {}, tested_at: null },
    { id: "tradingview", name: "TradingView", category: "signals", purpose: "", required: true, testable: false, steps: [], note: "",
      links: [], fields: [], status: "waiting", detail: "Waiting for the first TradingView heartbeat", hints: {}, tested_at: null },
  ],
  indicators: [], summary: { connected: 1, total: 2, required_ready: false }, webhook_path: "", master_key_set: true,
};

test("live statuses from the API, NO when something mandatory is missing", async () => {
  setup({
    "/api/connections": connections,
    "/api/webhook/status": { path: "", secret_set: true, feeds: [], accepted: {}, rejected: {}, last_rejection: null },
    "/api/today/plan": { calendar_loaded: true, attested_today: false, preflight: null },
  });
  const box = await screen.findByTestId("mandatory-checklist");
  await within(box).findByText("Key accepted");
  expect(await within(box).findByTestId("ready-line")).toHaveAttribute("data-ready", "no");
  expect(within(box).getByTestId("ready-line")).toHaveTextContent("Ready to trade EVAL/LIVE: NO");
  expect(within(box).getByTestId("check-broker")).toHaveAttribute("data-state", "ok");
  expect(within(box).getByTestId("check-heartbeat")).toHaveAttribute("data-state", "fail");
  expect(within(box).getByTestId("check-attestation")).toHaveAttribute("data-state", "fail");
  expect(within(box).getByTestId("check-calendar")).toHaveAttribute("data-state", "ok");
  expect(within(box).getByTestId("check-clock")).toHaveTextContent(/unknown — not measured yet: run pre-flight/);
  expect(within(box).getByTestId("check-preflight")).toHaveTextContent(/not run yet/);
});

test("API unreachable → items say unknown and the line is NOT CONFIRMED, never YES", async () => {
  setup({});
  const box = await screen.findByTestId("mandatory-checklist");
  expect(within(box).getByTestId("ready-line")).toHaveAttribute("data-ready", "unconfirmed");
  expect(within(box).getByTestId("ready-line")).toHaveTextContent("NOT CONFIRMED");
  expect(within(box).getByTestId("check-broker")).toHaveTextContent(/unknown — not available from the API/);
});
