import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BuildFooter, StaleUiBanner } from "./BuildGuard";
import { isStaleUi, short } from "../lib/build";

// deterministic UI commit, independent of git: the "UI" in these tests was built from abcdef1…
const UI_COMMIT = "abcdef1234567890";
vi.mock("../lib/build", async (orig) => ({ ...(await orig<typeof import("../lib/build")>()), UI_COMMIT: "abcdef1234567890" }));

function mount(ui: JSX.Element) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

function health(body: unknown, ok = true) {
  vi.stubGlobal("fetch", vi.fn(async () => (ok ? new Response(JSON.stringify(body), { status: 200 }) : Promise.reject(new Error("down")))));
}

afterEach(() => vi.unstubAllGlobals());

describe("isStaleUi", () => {
  it("flags only two known, different commits", () => {
    expect(isStaleUi("abcdef1234", "1234567890")).toBe(true);
    expect(isStaleUi("abcdef1234", "abcdef1")).toBe(false); // short vs full SHA
    expect(isStaleUi("dev", "1234567")).toBe(false);
    expect(isStaleUi("abcdef1", undefined)).toBe(false);
    expect(short("abcdef1234")).toBe("abcdef1");
    expect(short(undefined)).toBe("?");
  });
});

describe("BuildGuard", () => {
  beforeEach(() => health({ app: "paytience", build: { commit: "1234567890", built_at: "" }, started_at: "2026-11-11T08:00:00Z", executable: "Paytience.exe" }));

  it("shows the gold OLD-interface banner when UI and server commits differ", async () => {
    mount(<StaleUiBanner />);
    const b = await screen.findByTestId("banner-stale-ui");
    expect(b.textContent).toMatch(/OLD interface/);
    expect(b.textContent).toContain(`UI ${short(UI_COMMIT)}`);
    expect(b.textContent).toContain("server 1234567");
    expect(screen.getByRole("button", { name: /reload/i })).toBeTruthy();
  });

  it("shows no banner when the commits match", async () => {
    health({ app: "paytience", build: { commit: UI_COMMIT, built_at: "" } });
    mount(<StaleUiBanner />);
    await act(() => new Promise((r) => setTimeout(r, 30)));
    expect(screen.queryByTestId("banner-stale-ui")).toBeNull();
  });

  it("footer names the server, build, start time and UI commit", async () => {
    mount(<BuildFooter />);
    const f = await screen.findByText(/Server: Paytience\.exe · build 1234567/);
    expect(f.textContent).toContain(`UI ${short(UI_COMMIT)}`);
    expect(f.textContent).toMatch(/started /);
  });

  it("footer says so when the server is unreachable", async () => {
    health({}, false);
    mount(<BuildFooter />);
    expect(await screen.findByText(/Server: not reachable/)).toBeTruthy();
  });
});
