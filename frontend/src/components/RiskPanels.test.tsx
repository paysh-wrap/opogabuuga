import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { EvalModePanel } from "./RiskPanels";

const odds = (text: string) => ({ plan: "p", table: "regular", eod_on: true, text, pass_pct: 1, bust_pct: 1, last12_pass_pct: 1, last12_bust_pct: 1 });

function show(body: unknown) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify(body)));
  render(<QueryClientProvider client={new QueryClient()}><EvalModePanel /></QueryClientProvider>);
}

test("Evaluation Mode panel shows the server's eval odds for the active plan (D137), none hard-coded", async () => {
  show({ enabled: false, has_eval_accounts: true, confirm_phrase: "ENABLE EVALUATION MODE", odds: { regular: odds("pass 71% / bust 29% · last 12 mo 60/40 · EOD toggle ON"), high: odds("not measured yet") } });
  const main = await screen.findByTestId("eval-mode-main");
  await waitFor(() => expect(main).toHaveTextContent("pass 71%"));
  expect(main).toHaveTextContent("Regular, capped table: pass 71% / bust 29% · last 12 mo 60/40 · EOD toggle ON");
  expect(main).toHaveTextContent("High-risk table, grows larger: not measured yet");
  expect(main.textContent).not.toMatch(/83%|75\/24|69\/31|58\/42/); // the old session-19 figures are gone
});

test("without odds from the server the panel says not measured yet", async () => {
  show({ enabled: false, has_eval_accounts: false, confirm_phrase: "x" });
  expect(await screen.findByTestId("eval-mode-main")).toHaveTextContent("Regular, capped table: not measured yet");
});
