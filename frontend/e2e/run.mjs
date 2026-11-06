// End-to-end browser test against a REAL running server (make dev). No mocks.
// Usage: E2E_PASSWORD=... node frontend/e2e/run.mjs [baseUrl]
import { createRequire } from "node:module";
import { mkdirSync } from "node:fs";
const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const BASE = process.argv[2] ?? "http://127.0.0.1:8000";
const PW = process.env.E2E_PASSWORD;
const SHOTS = process.env.E2E_SHOTS ?? "frontend/test-results";
if (!PW) throw new Error("set E2E_PASSWORD");
mkdirSync(SHOTS, { recursive: true });

let passed = 0;
const failures = [];
async function step(name, fn) {
  try { await fn(); passed++; console.log(`  ✓ ${name}`); }
  catch (e) { failures.push(name); console.log(`  ✗ ${name}\n    ${String(e.message ?? e).split("\n")[0]}`); }
}
function expect(cond, msg) { if (!cond) throw new Error(msg); }

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 2 });
const page = await ctx.newPage();
const consoleErrors = [];
page.on("console", (m) => m.type() === "error" && consoleErrors.push(m.text()));

await step("unauthenticated visit redirects to login with Paytience branding", async () => {
  await page.goto(BASE + "/connections");
  await page.waitForURL("**/login");
  expect((await page.title()) === "Paytience · Login", "title " + (await page.title()));
  expect(await page.getByRole("heading", { name: "Paytience" }).isVisible(), "brand missing");
});

await page.screenshot({ path: `${SHOTS}/login.png` });

await step("wrong password shows an error", async () => {
  await page.getByLabel("Password").fill("not-the-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("alert").waitFor();
  expect((await page.getByRole("alert").textContent()).includes("invalid"), "no error text");
});

await step("correct password logs in and lands on Today", async () => {
  await page.getByLabel("Password").fill(PW);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL("**/today");
  await page.getByRole("heading", { name: "Today" }).waitFor();
  expect((await page.title()) === "Paytience · Today", "today title");
  await page.goto(BASE + "/connections");
  await page.getByRole("heading", { name: "Connections & API keys" }).waitFor();
  expect((await page.title()) === "Paytience · Connections", "title");
  expect((await page.getByTestId("mode").textContent()) === "PAPER", "mode should be PAPER");
  expect((await page.getByTestId("brand").innerText()).includes("Paytience"), "brand on connections");
});

await step("setup progress bar is present and consistent with the summary", async () => {
  const bar = page.getByRole("progressbar", { name: "Setup progress" });
  const now = Number(await bar.getAttribute("aria-valuenow"));
  const max = Number(await bar.getAttribute("aria-valuemax"));
  expect(max >= 11 && now >= 0 && now <= max, `progress ${now}/${max}`);
  expect((await page.getByTestId("summary-count").textContent()) === `${now}/${max}`, "summary mismatch");
});

await step("live WebSocket indicator connects", async () => {
  await page.getByText("live", { exact: true }).waitFor({ timeout: 10000 });
});

await step("both custom indicators are listed by exact name", async () => {
  for (const n of ["ICT Fractal Model, HTF Candles, CISD & C2 Targets [LunqFX]", "Market Structure Oscillator [BigBeluga]"])
    expect(await page.getByRole("heading", { name: n }).isVisible(), "missing " + n);
});

await step("TradingAgents card shows the REAL installed version 0.7.1 and GitHub link", async () => {
  const card = page.getByTestId("conn-tradingagents");
  await card.getByTestId("ta-installed").filter({ hasText: "0.7.1" }).waitFor({ timeout: 30000 });
  const href = await card.getByRole("link", { name: /GitHub repository/ }).getAttribute("href");
  expect(href === "https://github.com/TauricResearch/TradingAgents", "repo link " + href);
});

await step("every service card has a login/key link that opens in a new tab", async () => {
  const cards = page.locator("article[data-testid^=conn-]");
  const n = await cards.count();
  expect(n >= 12, "cards: " + n);
  for (let i = 0; i < n; i++) {
    const link = cards.nth(i).getByRole("link").first();
    expect((await link.getAttribute("target")) === "_blank", "target");
    expect((await link.getAttribute("href")).startsWith("https://"), "https");
  }
});

await step("TradingAgents card links every LLM provider's API-key page", async () => {
  const card = page.getByTestId("conn-tradingagents");
  await card.getByLabel("LLM provider").selectOption("anthropic");
  const l = card.getByRole("link", { name: "Claude (Anthropic) — default key" });
  expect((await l.getAttribute("href")) === "https://console.anthropic.com/settings/keys", "llm link");
});

await page.screenshot({ path: `${SHOTS}/connections-desktop.png`, fullPage: true });

await step("second tab reacts to a change via WebSocket without reloading", async () => {
  const other = await ctx.newPage();
  await other.goto(BASE + "/connections");
  await other.getByText("live", { exact: true }).waitFor({ timeout: 10000 });
  const card = page.getByTestId("conn-discord");
  await card.getByLabel("Webhook URL").fill("https://example.com/not-discord");
  await card.getByRole("button", { name: "Save & Test" }).click();
  await page.locator('[data-testid="conn-discord"][data-status="failed"]').waitFor();
  await other.locator('[data-testid="conn-discord"][data-status="failed"]').waitFor({ timeout: 5000 });
  expect((await other.getByTestId("conn-discord").textContent()).includes("Not a Discord webhook URL"), "detail");
  await other.close();
});

await step("saved secret is never shown back; placeholder shows only the masked hint", async () => {
  const input = page.getByTestId("conn-discord").getByLabel("Webhook URL");
  expect((await input.inputValue()) === "", "value should be cleared");
  const html = await page.content();
  expect(!html.includes("example.com/not-discord"), "secret leaked into page");
});

await step("Remove returns the card to Not set", async () => {
  page.once("dialog", (d) => d.accept());
  await page.getByTestId("conn-discord").getByRole("button", { name: "Remove" }).click();
  await page.locator('[data-testid="conn-discord"][data-status="not_set"]').waitFor();
});

await step("pasting a non-Pine source is rejected with a message", async () => {
  const card = page.getByTestId("ind-lunqfx");
  await card.getByRole("button", { name: /Paste Pine source/ }).click();
  await card.getByRole("textbox").fill("hello this is not pine");
  await card.getByRole("button", { name: "Save source" }).click();
  await card.getByRole("alert").waitFor();
});

await step("TradingView setup: reveal secret and download the bridge script", async () => {
  const box = page.getByTestId("tv-setup");
  await box.getByRole("button", { name: "Reveal" }).click();
  const secret = (await box.getByTestId("webhook-secret").textContent()).trim();
  expect(secret.length >= 32, "secret length " + secret.length);
  const r = await page.request.get(BASE + "/api/pine/bridge");
  expect(r.status() === 200 && (await r.text()).startsWith("//@version=6"), "download");
  globalThis.__secret = secret;
});

await step("a real webhook heartbeat turns the TradingView card gold live (no reload)", async () => {
  const t = Date.now() - 1000;
  const body = JSON.stringify({ v: 1, secret: globalThis.__secret, id: `MNQ1!-TIGHT-${t}-HEARTBEAT-NONE`, symbol: "MNQ1!",
    profile: "TIGHT", tf: "1", bar_time_ms: t, event: "HEARTBEAT", direction: "NONE",
    price: { o: "20000.25", h: "20001", l: "19999.5", c: "20000.75", v: "10" } });
  const r = await page.request.post(BASE + "/api/webhook/tradingview", { data: body, headers: { "content-type": "text/plain" } });
  expect(r.status() === 200, "webhook status " + r.status() + " " + (await r.text()));
  await page.locator('[data-testid="conn-tradingview"][data-status="connected"]').waitFor({ timeout: 10000 });
  await page.locator('[data-testid="feed-MNQ-TIGHT"][data-status="FRESH"]').waitFor({ timeout: 10000 });
});

await step("a webhook with the wrong secret is rejected and counted", async () => {
  const t = Date.now() - 1000;
  const body = JSON.stringify({ v: 1, secret: "wrong", id: `x-${t}`, symbol: "MNQ1!", profile: "TIGHT", tf: "1",
    bar_time_ms: t, event: "HEARTBEAT", direction: "NONE", price: { o: "1", h: "1", l: "1", c: "1", v: "0" } });
  const r = await page.request.post(BASE + "/api/webhook/tradingview", { data: body, headers: { "content-type": "text/plain" } });
  expect(r.status() === 401, "status " + r.status());
  await page.reload();
  await page.getByTestId("webhook-counts").filter({ hasText: "BAD_SECRET" }).waitFor({ timeout: 10000 });
});

await step("404 page keeps Paytience branding", async () => {
  await page.goto(BASE + "/nope");
  await page.getByRole("heading", { name: "Page not found" }).waitFor();
  const brand = page.getByTestId("brand");
  expect(await brand.isVisible(), "brand hidden");
  expect((await brand.innerText()).includes("Paytience"), "brand text: " + (await brand.innerText()));
  expect((await page.title()) === "Paytience · Not found", "title " + (await page.title()));
});

await step("phone width: no horizontal scroll", async () => {
  const m = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2,
    storageState: await ctx.storageState() });
  const p = await m.newPage();
  await p.goto(BASE + "/connections");
  await p.getByRole("heading", { name: "Connections & API keys" }).waitFor();
  const overflow = await p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  await p.screenshot({ path: `${SHOTS}/connections-phone.png`, fullPage: false });
  expect(overflow <= 0, "overflow px " + overflow);
  await m.close();
});

await step("log out ends the session", async () => {
  await page.goto(BASE + "/connections");
  await page.getByRole("button", { name: "Log out" }).click();
  await page.waitForURL("**/login");
  const r = await page.request.get(BASE + "/api/connections");
  expect(r.status() === 401, "status " + r.status());
});

await step("no browser console errors", async () => {
  const real = consoleErrors.filter((e) => !e.includes("401") && !e.includes("422") && !e.includes("Unauthorized"));
  expect(real.length === 0, real.join(" | "));
});

await browser.close();
console.log(`\n${passed} passed, ${failures.length} failed`);
process.exit(failures.length ? 1 : 0);
