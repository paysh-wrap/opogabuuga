import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import Today from "./Today";
import Dashboard from "./Dashboard";
import Payouts from "./Payouts";

const plan = {
  session: "2026-11-05", calendar_loaded: true,
  news: [{ at: "2026-11-05T13:30:00+00:00", title: "CPI", no_entry_from: "2026-11-05T13:15:00+00:00", no_entry_until: "2026-11-05T13:45:00+00:00", flatten_at: "2026-11-05T13:28:00+00:00" }],
  news_rules: { no_entry_before_min: 15, flatten_before_min: 2 },
  windows: [{ symbol: "MNQ", label: "Trading hours", windows: [["06:45", "09:30"]] }],
  accounts: [{ id: 1, label: "E1", stage: "EVAL", armed: true, selected: true }],
  attested_today: false, preflight: null, cooldowns: [],
  eval_pace: [{ id: 1, label: "E1", profit: "100", target: "1250", profitable_days: 1, min_profitable_days: 3, sessions_used: 2, target_sessions: 10, max_sessions: 20 }],
};
const acct = { id: 1, label: "E1", stage: "EVAL", paper: true, armed: true, paused: null, balance: "25000", open_pnl: "0", mll: "24000",
  to_mll: "150", kill_at: "100", max_loss: "1000", dll_limit: "600", dll_left: "250", today_pnl: "100", consistency_cap: "500",
  consistency_stop: "437.5", idle_days: 1, idle_delete_days: 7, trades_today: 1, fast_profit_pct: "0", fast_warn_pct: "20", fast_limit_pct: "50", fast_hold_s: 5 };

function mock(calls: string[]) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    const u = String(url);
    calls.push(`${init?.method ?? "GET"} ${u}`);
    const j = (o: unknown) => new Response(JSON.stringify(o));
    if (u === "/api/today/plan") return j(plan);
    if (u === "/api/today") return j({ signals: [], trades: [] });
    if (u === "/api/signals/skips") return j({ date: "2026-11-05", counts: { RR_BELOW_MIN: 3, WEIRD: 1 }, avg_20: { RR_BELOW_MIN: 1.5 }, sessions_in_avg: 4 });
    if (u === "/api/automation/preflight") return j({ ok: true, checks: {}, failures: [] });
    if (u === "/api/attestation") return j({ attested_today: true });
    if (u === "/api/dashboard") return j({ session: "2026-11-05", mode: "OFF", bias: {}, accounts: [acct] });
    if (u === "/api/pnl/daily") {
      const s = { days: [{ date: "2026-11-05", pnl: "290" }], weeks: [], total: "290" };
      return j({ household: s, accounts: [{ id: 1, label: "E1", stage: "EVAL", ...s, eval: { largest_day: "2026-11-05", largest_pnl: "290", limit_pct: "40", cap: "500", largest_pct: "100" } }] });
    }
    if (u === "/api/payouts") return j({ payouts: [] });
    return j({ decisions: [], events: [], loaded: true, error: null, markets: [] });
  });
}

function wrap(ui: JSX.Element) {
  render(<QueryClientProvider client={new QueryClient()}><MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>{ui}</MemoryRouter></QueryClientProvider>);
}

afterEach(() => vi.restoreAllMocks());

test("Today: blackouts, windows, pace, why-no-trade, and Ready runs attestation then pre-flight", async () => {
  const calls: string[] = [];
  mock(calls);
  wrap(<Today />);
  expect(await screen.findByText(/no entry .* flat by/)).toBeInTheDocument();
  expect(screen.getByText(/06:45–09:30/)).toBeInTheDocument();
  expect(screen.getByText(/profitable days 1\/3/)).toBeInTheDocument();
  expect(await screen.findByText("Reward:risk below minimum")).toBeInTheDocument();
  expect(screen.getByText("WEIRD", { selector: "td" })).toBeInTheDocument();
  const btn = screen.getByRole("button", { name: "Ready to trade" });
  expect(btn).toBeDisabled();
  await userEvent.click(screen.getByRole("checkbox"));
  await userEvent.click(btn);
  await waitFor(() => expect(screen.getByText(/Pre-flight passed/)).toBeInTheDocument());
  const order = calls.filter((c) => c.startsWith("POST"));
  expect(order).toEqual(["POST /api/attestation", "POST /api/automation/preflight"]);
});

test("Dashboard: rule-proximity meters use the safe/warn/danger bands", async () => {
  mock([]);
  wrap(<Dashboard />);
  const mll = await screen.findByTestId("meter-1-mll");
  expect(mll).toHaveAttribute("data-band", "danger"); // 150 of 1000 left = 85% used
  expect(screen.getByTestId("meter-1-dll")).toHaveAttribute("data-band", "warn"); // 250 of 600 left = 58% used
  expect(screen.getByTestId("meter-1-cons")).toHaveAttribute("data-band", "safe"); // 100/500
  expect(screen.getByTestId("meter-1-idle")).toHaveAttribute("data-band", "safe");
});

test("Payouts shows the daily P&L calendar with the largest day marked", async () => {
  mock([]);
  wrap(<Payouts />);
  const cells = await screen.findAllByTestId("cal-2026-11-05");
  expect(cells.length).toBe(2);
  expect(screen.getByText("largest day")).toBeInTheDocument();
  expect(screen.getByText(/Consistency line/)).toBeInTheDocument();
});
