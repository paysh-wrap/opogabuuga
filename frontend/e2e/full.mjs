// §21 Playwright E2E against a REAL server on a THROWAWAY scratch DB. `make e2e` runs this.
// Setup creates a temp dir + SQLite DB, migrates it, creates a test admin with a random in-memory password (never
// written anywhere), starts uvicorn on a free port with the scheduler off, runs the suite, then deletes everything.
// Never touches data/paytience.db. Uses the preinstalled Chromium (no browser download), no tracing.
import { createRequire } from "node:module";
import { execFileSync, spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { randomBytes } from "node:crypto";
import { createServer } from "node:net";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "../..");
const BACKEND = join(ROOT, "backend");
const PY = join(ROOT, ".venv/bin/python");
const SHOTS = process.env.E2E_SHOTS ?? join(ROOT, "frontend/test-results");
mkdirSync(SHOTS, { recursive: true });

const PAGES = [
  ["/dashboard", "Dashboard"], ["/today", "Today"], ["/signals", "Signals"], ["/trade", "Trade"], ["/accounts", "Accounts"],
  ["/strategy", "Strategy"], ["/backtest", "Backtest"], ["/lab", "Self-Learning Lab"], ["/replay", "Trade Replay"],
  ["/automation", "Automation"], ["/risk", "Risk management"], ["/payouts", "Payouts"], ["/connections", "Connections & API keys"],
  ["/journal", "Journal & Logs"], ["/settings", "Settings"], ["/does-not-exist", "Page not found"],
];

// ---------- scratch environment ----------
const tmp = mkdtempSync(join(tmpdir(), "paytience-e2e-"));
const dbUrl = `sqlite:///${join(tmp, "e2e.db")}`;
if (dbUrl.includes("data/paytience.db")) throw new Error("refusing to use the real database");
const password = randomBytes(18).toString("base64url"); // memory only
const env = {
  ...process.env,
  PAYTIENCE_DATABASE_URL: dbUrl,
  PAYTIENCE_RULES_PATH: join(ROOT, "config/rules/lucid_daily_25k.yaml"),
  PAYTIENCE_MASTER_KEY: randomBytes(32).toString("base64url") + "=",
  PAYTIENCE_WEBHOOK_SECRET: randomBytes(24).toString("hex"),
  PAYTIENCE_SCHEDULER_ENABLED: "false",
  PAYTIENCE_ALLOW_LIVE: "false",
  PAYTIENCE_WEB_DIST: join(ROOT, "frontend/dist"),
  PYTHONPATH: BACKEND,
  CI: "1",
};
delete env.PAYTIENCE_ADMIN_PASSWORD;

function freePort() {
  return new Promise((ok) => { const s = createServer(); s.listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => ok(p)); }); });
}

execFileSync(PY, ["-m", "alembic", "upgrade", "head"], { cwd: BACKEND, env, stdio: ["ignore", "ignore", "inherit"] });
execFileSync(PY, ["-m", "app.cli", "create-admin", "e2e"], { cwd: BACKEND, env: { ...env, PAYTIENCE_ADMIN_PASSWORD: password }, stdio: ["ignore", "ignore", "inherit"] });
const seed = (...args) => execFileSync(PY, [join(HERE, "seed.py"), ...args], { cwd: BACKEND, env, stdio: ["ignore", "ignore", "inherit"] });

seed("preflight");
const port = await freePort();
const BASE = `http://127.0.0.1:${port}`;
const server = spawn(PY, ["-m", "uvicorn", "app.main:create_app", "--factory", "--host", "127.0.0.1", "--port", String(port), "--log-level", "warning"],
  { cwd: BACKEND, env, stdio: ["ignore", "ignore", "inherit"] });
function cleanup() { try { server.kill("SIGTERM"); } catch { /* gone */ } rmSync(tmp, { recursive: true, force: true }); }
process.on("exit", cleanup);
for (let i = 0; ; i++) {
  try { if ((await fetch(BASE + "/api/health")).ok) break; } catch { /* starting */ }
  if (i > 120) throw new Error("server did not start");
  await new Promise((r) => setTimeout(r, 250));
}

// ---------- harness ----------
let passed = 0;
const failures = [];
async function step(name, fn) {
  if (process.env.E2E_ONLY && !process.env.E2E_ONLY.split("|").some((k) => name.includes(k)) && !name.includes("logs in") && !name.startsWith("login page")) return;
  try { await fn(); passed++; console.log(`  ✓ ${name}`); }
  catch (e) { failures.push(name); console.log(`  ✗ ${name}\n    ${String(e.message ?? e).split("\n").slice(0, 3).join("\n    ")}`); }
}
function expect(cond, msg) { if (!cond) throw new Error(msg); }

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
ctx.setDefaultTimeout(15000);
const page = await ctx.newPage();
page.on("dialog", (d) => d.accept());
const api = async (method, path, data) => {
  const csrf = (await ctx.cookies()).find((c) => c.name === "pt_csrf")?.value ?? "";
  const r = await page.request.fetch(BASE + path, { method, data, headers: { "x-csrf-token": csrf } });
  expect(r.ok(), `${method} ${path} → ${r.status()} ${await r.text()}`);
  return r.json();
};
// a real, signed TradingView heartbeat (the pre-flight needs a fresh feed)
const beat = async () => {
  const t = Date.now() - 1000;
  const r = await page.request.post(BASE + "/api/webhook/tradingview", { headers: { "content-type": "text/plain" }, data: JSON.stringify({
    v: 1, secret: env.PAYTIENCE_WEBHOOK_SECRET, id: `MNQ1!-TIGHT-${t}-HEARTBEAT-NONE`, symbol: "MNQ1!", profile: "TIGHT", tf: "1", bar_time_ms: t,
    event: "HEARTBEAT", direction: "NONE", price: { o: "20000.25", h: "20001", l: "19999.5", c: "20000.75", v: "10" } }) });
  expect(r.ok(), "heartbeat " + r.status() + " " + (await r.text()));
};
const goto = async (path, heading) => { await page.goto(BASE + path); await page.getByRole("heading", { name: heading, exact: true }).first().waitFor(); };

await step("login page carries Paytience branding; bad password is refused", async () => {
  await page.goto(BASE + "/dashboard");
  await page.waitForURL("**/login");
  expect((await page.title()) === "Paytience · Login", "title " + (await page.title()));
  await page.getByRole("heading", { name: "Paytience" }).waitFor();
  await page.getByLabel("Password").fill("wrong-" + password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("alert").waitFor();
});

await step("test admin logs in", async () => {
  const user = page.getByLabel("Username");
  if (await user.count()) await user.fill("e2e");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL("**/today");
});

// accounts used by the flows below (real API, paper sim accounts)
const eval1 = await api("POST", "/api/accounts", { label: "E1", stage: "EVAL" });
const sweep = await api("POST", "/api/accounts", { label: "F-sweep", stage: "FUNDED", balance: "28700" });
const skim = await api("POST", "/api/accounts", { label: "F-skim", stage: "FUNDED", balance: "27400" });
seed("profit", String(sweep.id), "100", "1");
seed("profit", String(skim.id), "1100", "1");
seed("cooldown");

await step('"Paytience" brand + tab title on every page (incl. 404)', async () => {
  for (const [path, heading] of PAGES) {
    await goto(path, heading);
    const brand = page.getByTestId("brand");
    expect((await brand.innerText()).includes("Paytience"), `brand on ${path}`);
    expect((await page.title()).startsWith("Paytience · "), `title on ${path}: ${await page.title()}`);
  }
});

await step("all buttons on every page have an accessible name and are keyboard focusable", async () => {
  for (const [path, heading] of PAGES) {
    await goto(path, heading);
    const bad = await page.evaluate(() => [...document.querySelectorAll("button")].filter((b) => {
      const name = (b.getAttribute("aria-label") ?? b.textContent ?? "").trim();
      return !name || b.tabIndex < 0;
    }).map((b) => b.outerHTML.slice(0, 80)));
    expect(bad.length === 0, `${path}: ${bad.join(" | ")}`);
  }
});

await step("external-positions attestation", async () => {
  await goto("/trade", "Trade");
  if (await page.getByTestId("attest").count()) {
    await page.getByRole("checkbox").first().check();
    await page.getByTestId("attest").click();
  }
  await page.getByTestId("attested").waitFor();
});

await step("automation OFF → SEMI; FULL refused in the first sessions of a stage; back OFF; header follows", async () => {
  await beat();
  await api("PATCH", `/api/accounts/${eval1.id}`, { armed: true }); // a session-1 EVAL account is armed
  await goto("/automation", "Automation");
  await page.getByTestId("mode-SEMI").click();
  await page.getByTestId("automation-mode").filter({ hasText: "SEMI" }).waitFor();
  const resp = page.waitForResponse((r) => r.url().endsWith("/api/automation") && r.request().method() === "PUT");
  await page.getByTestId("mode-FULL").click();
  const got = await (await resp).json().catch(() => ({}));
  expect(got.mode !== "FULL-AUTO" && got.mode !== "FULL", "FULL must be refused in the first sessions: " + JSON.stringify(got.granted) + JSON.stringify(await api("GET", "/api/accounts")).slice(0, 400));
  await page.waitForTimeout(500);
  expect(!(await page.getByTestId("automation-mode").innerText()).includes("FULL"), "header must not show FULL");
  await page.getByTestId("mode-OFF").click();
  await page.getByTestId("automation-mode").filter({ hasText: "OFF" }).waitFor();
  await api("PATCH", `/api/accounts/${eval1.id}`, { armed: false });
});

await step("approvals panel shows the SEMI-AUTO queue state", async () => {
  await beat();
  await api("PUT", "/api/automation", { mode: "SEMI" });
  await goto("/dashboard", "Dashboard");
  await page.getByTestId("dash-approvals").filter({ hasText: /Nothing waiting|Signal #/ }).waitFor();
  await goto("/trade", "Trade");
  await page.getByRole("heading", { name: "Approvals" }).waitFor();
  await api("PUT", "/api/automation", { mode: "OFF" });
});

await step("EVAL MODE: preview → typed phrase → gold badge → OFF", async () => {
  await goto("/risk", "Risk management");
  await page.getByTestId("eval-mode-preview").click();
  await page.getByTestId("eval-preview-on").waitFor();
  const enable = page.getByTestId("eval-mode-enable");
  expect(await enable.isDisabled(), "enable must wait for the phrase");
  await page.getByLabel("Evaluation Mode confirmation").fill("ENABLE EVALUATION MODE");
  await enable.click();
  const badge = page.getByTestId("eval-mode").filter({ hasText: "EVAL MODE ON" });
  await badge.waitFor();
  const color = await badge.evaluate((e) => getComputedStyle(e).color);
  expect(color === "rgb(212, 175, 55)", "badge not gold: " + color);
  await page.getByTestId("eval-mode-off").click();
  await page.getByTestId("eval-mode").filter({ hasText: "EVAL MODE OFF" }).waitFor();
});

await step("manual ticket runs every server check and reports the outcome", async () => {
  await goto("/trade", "Trade");
  const t = page.getByTestId("manual-ticket");
  await t.getByLabel("Ticket account").selectOption(String(eval1.id));
  await t.getByLabel("Ticket stop").fill("19950");
  await t.getByLabel("Ticket target").fill("20100");
  await t.getByTestId("ticket-submit").click();
  await page.getByTestId("ticket-msg").waitFor();
  expect((await page.getByTestId("ticket-msg").innerText()).length > 3, "no outcome text");
});

await step("account selector 1–5 updates Trading N of M", async () => {
  await goto("/accounts", "Accounts");
  await page.getByTestId("sel-2").click();
  await page.getByTestId("trading-n").filter({ hasText: "2 of 3" }).waitFor();
  await page.getByTestId("sel-1").click();
  await page.getByTestId("trading-n").filter({ hasText: "1 of 3" }).waitFor();
  await page.getByTestId(`history-${eval1.id}`).waitFor();
  expect((await page.getByRole("link", { name: /Open Lucid dashboard/ }).getAttribute("target")) === "_blank", "Lucid link");
});

await step("risk edit → preview → save → rollback", async () => {
  await goto("/risk", "Risk management");
  const before = await api("GET", "/api/risk/settings");
  await page.getByText(/Show all \d+ settings/).click();
  const input = page.getByLabel("internal.max_trades_per_day", { exact: true });
  const cur = await input.inputValue();
  await input.fill(String(Math.max(1, Number(cur) - 1)));
  expect(await page.getByTestId("risk-save").isDisabled(), "save must need a preview first");
  await page.getByTestId("risk-preview").click();
  await page.getByTestId("risk-impact").waitFor();
  await page.getByTestId("risk-save").click();
  const v1 = before.version + 1, saved = String(Math.max(1, Number(cur) - 1));
  await page.getByRole("heading", { name: `My settings · v${v1}` }).waitFor();
  await api("PUT", "/api/risk/settings", { changes: { "internal.max_trades_per_day": Number(cur) } }); // v1 + 1
  await page.reload();
  await page.getByRole("button", { name: `Roll back to v${v1}` }).click();
  await page.getByRole("heading", { name: `My settings · v${v1 + 2}` }).waitFor();
  const after = await api("GET", "/api/risk/settings");
  expect(String(after.settings["internal.max_trades_per_day"]) === saved, "rollback restored " + after.settings["internal.max_trades_per_day"]);
});

await step("cooldown banner + typed clear", async () => {
  await goto("/dashboard", "Dashboard");
  const b = page.getByTestId("cooldown-MNQ-TIGHT");
  await b.waitFor();
  await b.getByRole("button", { name: "Clear…" }).click();
  await b.getByLabel("Cooldown clear confirmation").fill("CLEAR COOLDOWN");
  await b.getByRole("button", { name: "Clear cooldown" }).click();
  await b.waitFor({ state: "detached" });
});

await step("payout tickets: sweep + skim → submitted → processed", async () => {
  await goto("/payouts", "Payouts");
  await page.getByRole("button", { name: "Check now" }).click();
  const rows = page.locator("[data-testid^=payout-]").filter({ hasText: /sweep|skim/ });
  await rows.nth(1).waitFor();
  const txt = await rows.allInnerTexts();
  expect(txt.some((t) => t.includes("sweep") && t.includes("$600.00")), "sweep $600: " + txt.join(" / "));
  expect(txt.some((t) => t.includes("skim") && t.includes("$550.00")), "skim $550: " + txt.join(" / "));
  for (let i = 0; i < 2; i++) {
    await rows.nth(i).getByRole("button", { name: "I requested it" }).click();
    await rows.nth(i).filter({ hasText: "submitted" }).waitFor();
    await rows.nth(i).getByRole("button", { name: "Paid" }).click();
    await rows.nth(i).filter({ hasText: "processed" }).waitFor();
  }
});

await step("backtest job: CSV import → job runs → results with payout simulation", async () => {
  await goto("/backtest", "Backtest");
  const lines = ["time,open,high,low,close,volume"];
  let px = 2650;
  for (const day of ["2026-10-26", "2026-10-27"]) {
    const t0 = Date.parse(`${day}T13:00:00Z`);
    for (let m = 0; m < 360; m++) {
      const o = px, c = Math.round((px + Math.sin(m / 9) * 0.8 + (m % 7 === 0 ? 0.4 : -0.1)) * 10) / 10;
      lines.push(`${new Date(t0 + m * 60000).toISOString()},${o},${Math.max(o, c) + 0.3},${Math.min(o, c) - 0.3},${c},10`);
      px = c;
    }
  }
  await page.getByLabel("CSV file").setInputFiles({ name: "e2e.csv", mimeType: "text/csv", buffer: Buffer.from(lines.join("\n")) });
  await page.getByRole("button", { name: "Run backtest" }).click();
  const run = page.locator("[data-testid^=bt-]").filter({ hasText: /— (done|failed)/ }).first();
  await run.waitFor({ timeout: 180000 });
  expect((await run.innerText()).includes("— done"), "backtest failed: " + (await run.innerText()).slice(0, 300));
});

await step("connections test alert is a dry run", async () => {
  await goto("/connections", "Connections & API keys");
  await page.getByLabel("Alert message").fill('{"v":1,"secret":"wrong"}');
  await page.getByRole("button", { name: "Check alert" }).click();
  await page.getByTestId("test-alert-result").waitFor();
});

await step("every API-key card: Save & Test a fake key → clear status, key never shown, Remove works", async () => {
  const list = (await api("GET", "/api/connections")).connections;
  const cards = list.filter((c) => (c.fields ?? []).length > 0);
  expect(cards.length >= 8, "only " + cards.length + " key cards");
  const bad = [];
  for (const c of cards) {
    const fake = "e2e-FAKE-" + randomBytes(6).toString("hex");
    const values = {};
    for (const f of c.fields) values[f.key ?? f.name] = f.kind === "select" || f.type === "select" ? f.options[0] : (f.kind === "secret" || f.type === "secret" || /key|token|secret|password/i.test(f.key ?? f.name) ? fake : "e2e");
    const csrf = (await ctx.cookies()).find((k) => k.name === "pt_csrf")?.value ?? "";
    const r = await page.request.fetch(`${BASE}/api/connections/${c.id}`, { method: "PUT", data: { values }, headers: { "x-csrf-token": csrf } });
    const body = await r.text();
    if (r.status() >= 500) { bad.push(`${c.id}: HTTP ${r.status()}`); continue; }
    if (body.includes(fake)) bad.push(`${c.id}: key echoed back`);
    if (r.ok()) {
      const v = JSON.parse(body);
      if (!["failed", "saved", "connected"].includes(v.status)) bad.push(`${c.id}: status ${v.status}`);
    }
    await goto("/connections", "Connections & API keys");
    if ((await page.content()).includes(fake)) bad.push(`${c.id}: key visible on page`);
    const d = await page.request.fetch(`${BASE}/api/connections/${c.id}`, { method: "DELETE", headers: { "x-csrf-token": csrf } });
    if (!d.ok()) bad.push(`${c.id}: remove ${d.status()}`);
    console.log(`    · ${c.id}: ${r.status()} ${r.ok() ? JSON.parse(body).status + " — " + String(JSON.parse(body).detail).slice(0, 70) : body.slice(0, 80)}`);
  }
  expect(bad.length === 0, bad.join("; "));
});

await step("kill switch: typed KILL → automation OFF, accounts disarmed", async () => {
  await beat();
  await api("PUT", "/api/automation", { mode: "SEMI" });
  await goto("/dashboard", "Dashboard");
  await page.getByRole("button", { name: "KILL SWITCH" }).click();
  await page.getByLabel("Kill switch confirmation").fill("KILL");
  await page.getByRole("button", { name: "Confirm kill" }).click();
  await page.getByTestId("automation-mode").filter({ hasText: "OFF" }).waitFor();
  const a = await api("GET", "/api/accounts");
  expect(a.accounts.every((x) => !x.armed), "all disarmed");
});

// ---------- WCAG AA over the rendered pages (§18/§21) ----------
const CONTRAST = () => {
  const rgb = (s) => (s.match(/[\d.]+/g) ?? []).map(Number);
  const lum = ([r, g, b]) => [r, g, b].map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; })
    .reduce((s, v, i) => s + v * [0.2126, 0.7152, 0.0722][i], 0);
  const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
  const bgOf = (el) => {
    const layers = [];
    for (let e = el; e; e = e.parentElement) {
      const c = rgb(getComputedStyle(e).backgroundColor);
      if (c.length >= 3 && (c[3] ?? 1) > 0) { layers.push(c); if ((c[3] ?? 1) >= 1) break; }
    }
    let base = layers.length && (layers.at(-1)[3] ?? 1) >= 1 ? layers.pop() : [10, 16, 32];
    while (layers.length) { const c = layers.pop(); const a = c[3]; base = [0, 1, 2].map((i) => c[i] * a + base[i] * (1 - a)); }
    return base;
  };
  const out = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const seen = new Set();
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const el = n.parentElement;
    if (!el || seen.has(el) || !n.textContent.trim()) continue;
    seen.add(el);
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    if (cs.visibility === "hidden" || cs.display === "none" || r.width === 0 || el.closest("[aria-hidden=true],option,svg")) continue;
    const fg = rgb(cs.color), bg = bgOf(el);
    const size = parseFloat(cs.fontSize), bold = Number(cs.fontWeight) >= 700;
    const need = size >= 24 || (bold && size >= 18.66) ? 3 : 4.5;
    const k = ratio(fg, bg);
    if (k < need) out.push(`${el.tagName} "${n.textContent.trim().slice(0, 30)}" ${cs.color} on rgb(${bg.map(Math.round)}) = ${k.toFixed(2)}`);
  }
  return out;
};

await step("WCAG AA contrast on every rendered page", async () => {
  const bad = [];
  for (const [path, heading] of PAGES) {
    await goto(path, heading);
    await page.waitForTimeout(300);
    for (const v of await page.evaluate(CONTRAST)) bad.push(`${path}: ${v}`);
  }
  await page.goto(BASE + "/login");
  expect(bad.length === 0, `${bad.length} low-contrast texts:\n${bad.slice(0, 12).join("\n")}`);
});

// ---------- phone width (§24.4) ----------
await step("390 px: no horizontal scroll on any page and the nav reaches every page", async () => {
  const m = await browser.newContext({ viewport: { width: 390, height: 844 }, storageState: await ctx.storageState() });
  const p = await m.newPage();
  const bad = [];
  for (const [path, heading] of PAGES) {
    await p.goto(BASE + path);
    await p.getByRole("heading", { name: heading, exact: true }).first().waitFor();
    await p.waitForTimeout(200);
    const over = await p.evaluate(() => {
      const w = window.innerWidth, d = document.documentElement.scrollWidth - w;
      if (d <= 0) return null;
      const clipped = (e) => { for (let a = e.parentElement; a && a !== document.body; a = a.parentElement) if (getComputedStyle(a).overflowX !== "visible") return true; return false; };
      const off = [...document.querySelectorAll("body *")].filter((e) => !clipped(e) && e.getBoundingClientRect().right > w + 1 && ![...e.children].some((c) => c.getBoundingClientRect().right > w + 1))
        .slice(0, 3).map((e) => `${e.tagName}.${String(e.className).slice(0, 40)} "${(e.textContent ?? "").trim().slice(0, 25)}"`);
      return `${d}px (${off.join(", ")})`;
    });
    if (over) bad.push(`${path} overflows ${over}`);
    await p.screenshot({ path: join(SHOTS, `phone${path.replace(/\//g, "-")}.png`) });
  }
  await p.goto(BASE + "/dashboard");
  const links = p.getByRole("navigation", { name: "Main" }).getByRole("link");
  const n = await links.count();
  const last = links.nth(n - 1);
  await last.scrollIntoViewIfNeeded();
  await last.click();
  await p.waitForURL("**/settings");
  await m.close();
  expect(bad.length === 0, bad.join("; "));
});

await step("log out ends the session", async () => {
  await page.goto(BASE + "/dashboard");
  await page.getByRole("button", { name: "Log out" }).click();
  await page.waitForURL("**/login");
});

await browser.close();
console.log(`\n${passed} passed, ${failures.length} failed`);
cleanup();
process.exit(failures.length ? 1 : 0);
