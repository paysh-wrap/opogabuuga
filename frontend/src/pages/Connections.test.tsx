import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import Connections from "./Connections";
import type { Connection, ConnectionsResponse } from "../lib/api";

const base: Omit<Connection, "id" | "name" | "status"> = {
  category: "data", purpose: "p", required: false, testable: true, steps: [], note: "",
  links: [{ label: "API keys", url: "https://databento.com/portal/keys" }],
  fields: [{ name: "api_key", label: "API key", kind: "secret", required: true, placeholder: "", options: [], help: "" }],
  detail: "", hints: {}, tested_at: null,
};

function payload(status: Connection["status"], hints: Record<string, string> = {}): ConnectionsResponse {
  return {
    connections: [{ ...base, id: "databento", name: "Databento (historical futures data)", status, hints,
      detail: status === "connected" ? "Key accepted" : "" }],
    indicators: [{ id: "bigbeluga_mso", name: "Market Structure Oscillator [BigBeluga]", author: "BigBeluga",
      role: "WHERE / WHAT", link: "https://www.tradingview.com/scripts/search/x/", setting: "Require C2 to close back inside C1 = ON",
      source_on_file: false, license: null, personal_use_only: null, alerts_status: "waiting", alerts_detail: "Waiting" }],
    summary: { connected: status === "connected" ? 1 : 0, total: 1, required_ready: false },
    webhook_path: "/api/webhook/tradingview", master_key_set: true,
  };
}

function setup(responses: ConnectionsResponse[]) {
  let i = 0;
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    if (String(url) === "/api/connections" && (!init || !init.method || init.method === "GET"))
      return new Response(JSON.stringify(responses[Math.min(i++, responses.length - 1)]));
    if (String(url) === "/api/webhook/status")
      return new Response(JSON.stringify({ path: "/api/webhook/tradingview", secret_set: true,
        feeds: [{ symbol: "MNQ", profile: "TIGHT", last_heartbeat: null, data_feed: "delayed", status: "FRESH" }], accepted: { HEARTBEAT: 3 },
        rejected: {}, last_rejection: null }));
    return new Response(JSON.stringify({}));
  });
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><Connections /></MemoryRouter>
    </QueryClientProvider>,
  );
  return fetchMock;
}

afterEach(() => vi.restoreAllMocks());

test("shows indicator names, external links in new tab, and Not set status", async () => {
  setup([payload("not_set")]);
  expect(await screen.findByText("Market Structure Oscillator [BigBeluga]")).toBeInTheDocument();
  const card = screen.getByTestId("conn-databento");
  expect(within(card).getByTestId("status")).toHaveAttribute("data-status", "not_set");
  const link = within(card).getByRole("link", { name: /API keys/ });
  expect(link).toHaveAttribute("target", "_blank");
  expect(link).toHaveAttribute("rel", "noopener noreferrer");
  expect(document.title).toBe("Paytience · Connections");
});

test("Save & Test sends PUT with the key, then the card reacts to Connected", async () => {
  const f = setup([payload("not_set"), payload("connected", { api_key: "••••1234" })]);
  const card = await screen.findByTestId("conn-databento");
  await userEvent.type(within(card).getByLabelText("API key"), "db-secret-1234");
  await userEvent.click(within(card).getByRole("button", { name: "Save & Test" }));
  const put = f.mock.calls.find(([, init]) => init?.method === "PUT")!;
  expect(put[0]).toBe("/api/connections/databento");
  expect(JSON.parse(String(put[1]!.body))).toEqual({ values: { api_key: "db-secret-1234" } });
  const updated = await screen.findByText(/Key accepted/);
  expect(updated).toBeInTheDocument();
  expect(screen.getByTestId("conn-databento")).toHaveAttribute("data-status", "connected");
  expect(within(screen.getByTestId("conn-databento")).getByLabelText("API key")).toHaveValue("");
  expect(within(screen.getByTestId("conn-databento")).getByLabelText("API key"))
    .toHaveAttribute("placeholder", "saved ••••1234 — leave blank to keep");
});

test("TradingView setup shows download link, masked secret and live feed status", async () => {
  setup([payload("not_set")]);
  const box = await screen.findByTestId("tv-setup");
  expect(within(box).getByTestId("download-bridge")).toHaveAttribute("href", "/api/pine/bridge");
  expect(await within(box).findByRole("button", { name: "Reveal" })).toBeInTheDocument();
  expect(await within(box).findByTestId("feed-MNQ-TIGHT")).toHaveAttribute("data-status", "FRESH");
  expect(within(box).getByTestId("webhook-counts")).toHaveTextContent("HEARTBEAT 3");
});

function ngrokPayload(tunnel: NonNullable<Connection["tunnel"]>): ConnectionsResponse {
  const p = payload("not_set");
  p.connections = [{ ...base, id: "ngrok", name: "ngrok (permanent webhook URL)", category: "network", status: "connected",
    links: [{ label: "1. Sign up (free)", url: "https://dashboard.ngrok.com/signup" }], tunnel,
    fields: [
      { name: "authtoken", label: "ngrok authtoken", kind: "secret", required: true, placeholder: "", options: [], help: "" },
      { name: "domain", label: "Static domain", kind: "text", required: true, placeholder: "", options: [], help: "" },
    ] }];
  return p;
}

test("ngrok active: permanent webhook URL and note", async () => {
  setup([ngrokPayload({ mode: "ngrok", ngrok_domain: "me.ngrok-free.app", public_url: "https://me.ngrok-free.app", permanent: true, error: "" })]);
  expect(await screen.findByTestId("ngrok-status")).toHaveTextContent("Active: https://me.ngrok-free.app (permanent)");
  expect(await screen.findByTestId("webhook-url")).toHaveTextContent("https://me.ngrok-free.app/api/webhook/tradingview");
  expect(screen.getByTestId("permanent-note")).toHaveTextContent("permanent — set once in TradingView");
  expect(screen.queryByTestId("tunnel-banner")).toBeNull();
  expect(screen.getByRole("link", { name: /Sign up/ })).toHaveAttribute("href", "https://dashboard.ngrok.com/signup");
});

test("ngrok failed: Cloudflare fallback banner is shown", async () => {
  setup([ngrokPayload({ mode: "cloudflare", public_url: "https://x.trycloudflare.com", permanent: false, error: "ngrok keeps failing" })]);
  expect(await screen.findByTestId("tunnel-banner")).toHaveTextContent("temporary Cloudflare link");
  expect(screen.queryByTestId("permanent-note")).toBeNull();
});

test("D93: only mandatory EVAL/LIVE connections get the standout tag; optional ones keep the normal colour", async () => {
  const p = payload("not_set");
  p.connections = [
    { ...base, id: "crosstrade", name: "CrossTrade (Tradovate orders + positions)", category: "broker", status: "not_set" },
    { ...base, id: "discord", name: "Discord (notifications)", category: "notifications", status: "connected" },
  ];
  setup([p]);
  const ct = await screen.findByTestId("conn-crosstrade");
  expect(ct).toHaveAttribute("data-mandatory", "true");
  expect(ct.className).toContain("mandatory-card");
  expect(within(ct).getByTestId("mandatory-tag")).toHaveTextContent("MANDATORY");
  const dc = screen.getByTestId("conn-discord");
  expect(dc).not.toHaveAttribute("data-mandatory");
  expect(within(dc).queryByTestId("mandatory-tag")).toBeNull();
  expect(screen.getByTestId("mandatory-checklist")).toBeInTheDocument();
});

test("shows the CME real-time data chip (D112)", async () => {
  setup([payload("not_set")]);
  await screen.findByTestId("cme-realtime");
  await waitFor(() => expect(screen.getByTestId("cme-realtime")).toHaveTextContent("CME real-time data: DELAYED"));
});
