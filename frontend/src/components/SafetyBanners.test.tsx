import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import SafetyBanners, { type Safety } from "./SafetyBanners";
import FeedGuardSettings from "./FeedGuardSettings";

const full: Safety = {
  unmanaged: [{ account: "E1", reason: "RESTART_UNMANAGED" }, { account: "E2", reason: "RESTART_UNVERIFIED" }],
  feed: [{ symbol: "MNQ", state: "WARN" }],
  pending_exits: [{ signal_id: 4, symbol: "MNQ", reason: "NOISE_TRAIL", since: null }],
  missed_checks: [{ symbol: "MNQ", minute_et: "10:30", key: "k" }],
};

function wrap(body: Safety) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify(body)));
  render(<QueryClientProvider client={new QueryClient()}><MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><SafetyBanners /></MemoryRouter></QueryClientProvider>);
}
afterEach(() => vi.restoreAllMocks());

test("every new safety state is shown in plain language", async () => {
  wrap(full);
  const un = await screen.findAllByTestId("banner-unmanaged");
  expect(un[0]).toHaveTextContent("Restart found an unmanaged position");
  expect(un[0]).toHaveTextContent("flattened it and paused");
  expect(un[1]).toHaveTextContent("could not read the broker");
  expect(screen.getByTestId("banner-feed-MNQ")).toHaveTextContent("Price feed lost while in a position");
  expect(screen.getByTestId("banner-missed-check")).toHaveTextContent("Missed check minute 10:30");
  expect(screen.getByTestId("banner-exit-pending")).toHaveTextContent("Exit pending broker confirmation");
});

test("a lost feed past the flatten limit says the position is being closed", async () => {
  wrap({ unmanaged: [], feed: [{ symbol: "MNQ", state: "LOST" }], pending_exits: [], missed_checks: [] });
  expect(await screen.findByTestId("banner-feed-MNQ")).toHaveTextContent("being closed (FEED_LOST)");
});

test("nothing wrong shows nothing", async () => {
  wrap({ unmanaged: [], feed: [], pending_exits: [], missed_checks: [] });
  await act(() => new Promise((r) => setTimeout(r, 50)));
  expect(screen.queryByTestId("safety-banners")).toBeNull();
});

test("feed-protection control saves validated thresholds and the on/off switch", async () => {
  const saved: Record<string, unknown>[] = [];
  const save = (c: Record<string, unknown>) => saved.push(c);
  render(<FeedGuardSettings settings={{ "reliability.feed_guard_enabled": true, "reliability.feed_warn_min": 3, "reliability.feed_flatten_min": 6 }} save={save} />);
  expect(screen.getByRole("heading")).toHaveTextContent("ON");
  await userEvent.click(screen.getByTestId("feed-guard-on"));
  expect(saved[0]).toEqual({ "reliability.feed_guard_enabled": false });
  const warn = screen.getByLabelText("Warn after minutes");
  await userEvent.clear(warn);
  await userEvent.type(warn, "7");
  expect(screen.getByTestId("feed-guard-save")).toBeDisabled();
  expect(screen.getByRole("alert")).toHaveTextContent("larger than warn-after");
  await userEvent.clear(warn);
  await userEvent.type(warn, "2");
  await userEvent.click(screen.getByTestId("feed-guard-save"));
  expect(saved[1]).toEqual({ "reliability.feed_warn_min": 2, "reliability.feed_flatten_min": 6 });
});
