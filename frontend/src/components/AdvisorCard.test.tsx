import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AdvisorCard, { AdvisorBadge, AdvisorCardLine, type AdvisorResp } from "./AdvisorCard";

const card = { mode: "GALA_PA", symbol: "MNQ", skipped: false, call_label: null, call_direction: null, prob_up: null, last_verdict: null };
const adv = (o: Partial<AdvisorResp> = {}): AdvisorResp => ({
  mode: "ADVISORY", setting: "strategy.advisor.mode", skip_strategies: [], connected: false, ledger_proven: false, required_accuracy: 0.7,
  cards: { gala_pa: card, conti_orb: { ...card, mode: "CONTI_ORB", call_label: "SELL", call_direction: -1, prob_up: 0.45, last_verdict: "DISAGREE" } }, ...o,
});
const wrap = (el: React.ReactElement) => render(<QueryClientProvider client={new QueryClient()}>{el}</QueryClientProvider>);

test("badges show the four verdicts in gold/blue text", () => {
  render(<>{(["AGREE", "DISAGREE", "NEUTRAL", "NO_CALL"] as const).map((v) => <AdvisorBadge key={v} verdict={v} testId={`b-${v}`} />)}</>);
  expect(screen.getByTestId("b-NO_CALL")).toHaveTextContent("ADVISOR · NO CALL");
  expect(screen.getByTestId("b-DISAGREE").className).toContain("text-gold");
  expect(screen.getByTestId("b-NEUTRAL").className).toContain("text-blue");
});

test("card lines: no call, latest verdict, off", () => {
  const { rerender } = render(<><AdvisorCardLine adv={adv()} cardKey="gala_pa" /><AdvisorCardLine adv={adv()} cardKey="conti_orb" /><AdvisorCardLine adv={adv()} cardKey="noise" /></>);
  expect(screen.getByTestId("advisor-gala_pa")).toHaveTextContent("NO CALL");
  expect(screen.getByTestId("advisor-gala_pa")).toHaveTextContent("no call today");
  expect(screen.getByTestId("advisor-conti_orb")).toHaveTextContent("ADVISOR · DISAGREE today: ▼ SHORT (P up 45%)");
  expect(screen.queryByTestId("advisor-noise")).toBeNull();
  rerender(<AdvisorCardLine adv={adv({ mode: "OFF" })} cardKey="gala_pa" />);
  expect(screen.getByTestId("advisor-gala_pa")).toHaveTextContent("off for this strategy");
});

test("mode control saves a versioned setting; key note and unproven gate note", async () => {
  const calls: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    calls.push(`${init?.method ?? "GET"} ${String(url)} ${init?.body ? String(init.body) : ""}`);
    return new Response(JSON.stringify(String(url) === "/api/strategies" ? { advisor: adv({ mode: "GATE" }) } : {}));
  });
  wrap(<AdvisorCard />);
  expect(await screen.findByTestId("advisor-no-key")).toHaveTextContent("TradingAgents key not connected: no call today");
  expect(screen.getByTestId("advisor-gate-unproven")).toHaveTextContent("behaves like Advisory");
  await userEvent.click(screen.getByRole("button", { name: "Off" }));
  await waitFor(() => expect(calls.some((c) => c.includes('"strategy.advisor.mode":"OFF"'))).toBe(true));
});

test("connected without a call today says so", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify({ advisor: adv({ connected: true, cards: { gala_pa: card } }) })));
  wrap(<AdvisorCard />);
  expect(await screen.findByTestId("advisor-no-call")).toHaveTextContent("blocks nothing");
  expect(screen.queryByTestId("advisor-no-key")).toBeNull();
});
