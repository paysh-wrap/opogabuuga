import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { UpdateBanner } from "./UpdatePanel";

const status = {
  version: { commit: "abcdef1234", built_at: "" },
  desktop: true,
  token_set: true,
  last_check: { available: true, commit: "1234567890", error: "" },
  failed_update: null,
  blocked: null,
};

describe("UpdateBanner install", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (String(url).includes("/api/updates/install")) return new Response(JSON.stringify({ ok: true, restarting: true }), { status: 200 });
        return new Response(JSON.stringify(status), { status: 200 });
      }),
    );
  });
  afterEach(() => vi.unstubAllGlobals());

  it("shows the new-server restart notice after Install now", async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <UpdateBanner />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    const btn = await screen.findByRole("button", { name: /install now/i });
    btn.click();
    expect(await screen.findByTestId("update-restart-notice")).toBeTruthy();
    expect(screen.getByText(/NEW Paytience server is starting/i)).toBeTruthy();
  });
});
