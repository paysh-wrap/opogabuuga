import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import Signals from "./Signals";
import Journal, { toCsv } from "./Journal";
import HeaderStatus from "../components/HeaderStatus";

function mock(calls: string[]) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    const u = String(url);
    calls.push(`${init?.method ?? "GET"} ${u}`);
    const j = (o: unknown) => new Response(JSON.stringify(o));
    if (u.startsWith("/api/signals")) return j({ signals: [{ id: 7, symbol: "MNQ", profile: "TIGHT", direction: "LONG", status: "SKIP",
      skip_reason: "RR_BELOW_MIN", score: "72", c1_range_atr: "1.2", confirmed_at: "2026-11-05T15:00:00+00:00",
      gates: [{ gate: "G1", passed: true }, { gate: "G7", passed: false, code: "RR_BELOW_MIN" }],
      plans: [{ mode: "OFF", entry: "20000", stop: "19981", take_profit: "20040", rr: "2.1" }] }] });
    if (u.startsWith("/api/logs")) return j({ logs: [{ id: 1, at: "2026-11-05T15:00:00+00:00", actor: "admin", action: "cooldown.cleared", entity: "TIGHT", payload: { rows: 1 } }],
      actions: ["cooldown.cleared"], chain_ok: true, chain_first_bad_id: null });
    if (u === "/api/automation") return j({ mode: "SEMI-AUTO" });
    if (u === "/api/risk/eval-mode") return j({ enabled: true });
    if (u === "/api/accounts") return j({ accounts: [{ id: 1, armed: true, selected: true }, { id: 2, armed: false, selected: true }] });
    if (u === "/api/rules") return j({ rules: { internal: { auto_flatten: "16:40" } } });
    if (u === "/api/kill-switch") return j({ killed: true });
    return j({});
  });
}
function wrap(ui: JSX.Element) {
  render(<QueryClientProvider client={new QueryClient()}><MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>{ui}</MemoryRouter></QueryClientProvider>);
}
afterEach(() => vi.restoreAllMocks());

test("Signals shows gates, reason and plan prices", async () => {
  mock([]);
  wrap(<Signals />);
  expect(await screen.findByTestId("signal-7")).toHaveTextContent("RR_BELOW_MIN");
  expect(screen.getByTestId("signal-7")).toHaveTextContent("▲ LONG");
  await userEvent.click(screen.getByRole("button", { name: "Plan" }));
  expect(screen.getByTestId("plan-7")).toHaveTextContent("19981");
  expect(document.title).toBe("Paytience · Signals");
});

test("Journal lists logs, reports the chain and builds CSV", async () => {
  mock([]);
  wrap(<Journal />);
  expect(await screen.findByTestId("log-1")).toHaveTextContent("cooldown.cleared");
  expect(screen.getByTestId("chain")).toHaveTextContent("intact");
  expect(toCsv([{ id: 1, at: "t", actor: "a,b", action: "x", entity: "", payload: { k: 1 } }])).toContain('"a,b"');
});

test("Header status shows mode, eval mode, trading count, countdown; kill needs typed KILL", async () => {
  const calls: string[] = [];
  mock(calls);
  wrap(<HeaderStatus />);
  expect(await screen.findByTestId("automation-mode")).toHaveTextContent("SEMI");
  expect(await screen.findByTestId("eval-mode")).toHaveTextContent("EVAL MODE ON");
  expect(await screen.findByTestId("trading-count")).toHaveTextContent("1 of 2");
  expect(await screen.findByTestId("flatten-countdown")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "KILL SWITCH" }));
  const confirm = screen.getByRole("button", { name: "Confirm kill" });
  expect(confirm).toBeDisabled();
  await userEvent.type(screen.getByLabelText("Kill switch confirmation"), "KILL");
  await userEvent.click(confirm);
  expect(calls).toContain("POST /api/kill-switch");
});
