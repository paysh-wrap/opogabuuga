// Full-page screenshots of EVERY Paytience page: real server on a THROWAWAY scratch DB (same setup as full.mjs),
// Pro 25K plan, one paper EVAL account, pre-flight fixtures. Never touches data/paytience.db.
// Usage: (cd frontend && npm run build) && node frontend/e2e/all-shots.mjs [outdir] [width]
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
const OUT = resolve(process.argv[2] ?? join(ROOT, "docs/results/ui/all_pages"));
const WIDTH = Number(process.argv[3] ?? 1440);
mkdirSync(OUT, { recursive: true });

const PAGES = [
  ["01_today", "/today"], ["02_dashboard", "/dashboard"], ["03_signals", "/signals"], ["04_trade", "/trade"],
  ["05_accounts", "/accounts"], ["06_strategy", "/strategy"], ["07_backtest", "/backtest"], ["08_lab", "/lab"],
  ["09_replay", "/replay"], ["10_orderflow", "/orderflow"], ["11_automation", "/automation"], ["12_risk", "/risk"],
  ["13_payouts", "/payouts"], ["14_connections", "/connections"], ["15_journal", "/journal"], ["16_settings", "/settings"],
];

const tmp = mkdtempSync(join(tmpdir(), "paytience-e2e-")); // seed.py only accepts this prefix
const dbUrl = `sqlite:///${join(tmp, "e2e.db")}`;
const password = randomBytes(18).toString("base64url"); // memory only
const env = {
  ...process.env, PAYTIENCE_DATABASE_URL: dbUrl,
  PAYTIENCE_RULES_PATH: join(ROOT, "config/rules/lucid_pro_25k.yaml"),
  PAYTIENCE_MASTER_KEY: randomBytes(32).toString("base64url") + "=", PAYTIENCE_WEBHOOK_SECRET: randomBytes(24).toString("hex"),
  PAYTIENCE_SCHEDULER_ENABLED: "false", PAYTIENCE_ALLOW_LIVE: "false", PAYTIENCE_WEB_DIST: join(ROOT, "frontend/dist"),
  PYTHONPATH: BACKEND, CI: "1",
};
delete env.PAYTIENCE_ADMIN_PASSWORD;
const freePort = () => new Promise((ok) => { const s = createServer(); s.listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => ok(p)); }); });
execFileSync(PY, ["-m", "alembic", "upgrade", "head"], { cwd: BACKEND, env, stdio: ["ignore", "ignore", "inherit"] });
execFileSync(PY, ["-m", "app.cli", "create-admin", "e2e"], { cwd: BACKEND, env: { ...env, PAYTIENCE_ADMIN_PASSWORD: password }, stdio: ["ignore", "ignore", "inherit"] });
execFileSync(PY, [join(HERE, "seed.py"), "preflight"], { cwd: BACKEND, env, stdio: ["ignore", "ignore", "inherit"] });
const port = await freePort();
const BASE = `http://127.0.0.1:${port}`;
const server = spawn(PY, ["-m", "uvicorn", "app.main:create_app", "--factory", "--host", "127.0.0.1", "--port", String(port), "--log-level", "warning"],
  { cwd: BACKEND, env, stdio: ["ignore", "ignore", "inherit"] });
process.on("exit", () => { try { server.kill("SIGTERM"); } catch { /* gone */ } rmSync(tmp, { recursive: true, force: true }); });
for (let i = 0; ; i++) {
  try { if ((await fetch(BASE + "/api/health")).ok) break; } catch { /* starting */ }
  if (i > 120) throw new Error("server did not start");
  await new Promise((r) => setTimeout(r, 250));
}

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: WIDTH, height: 900 }, deviceScaleFactor: 2, reducedMotion: "reduce" });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e.message ?? e)));
await page.goto(BASE + "/login");
await page.waitForLoadState("networkidle").catch(() => {});
await page.screenshot({ path: join(OUT, "00_login.jpg"), type: "jpeg", quality: 85 });
console.log("  saved 00_login.jpg");
const user = page.getByLabel("Username");
if (await user.count()) await user.fill("e2e");
await page.getByLabel("Password").fill(password);
await page.getByRole("button", { name: "Sign in" }).click();
await page.waitForURL("**/today");
const csrf = (await ctx.cookies()).find((c) => c.name === "pt_csrf")?.value ?? "";
const acc = await page.request.post(BASE + "/api/accounts", {
  data: { label: "Pro 25K eval (paper)", stage: "EVAL", balance: "25000" }, headers: { "x-csrf-token": csrf },
});
if (!acc.ok()) console.log(`  ! account create ${acc.status()}`);
for (const [name, path] of PAGES) {
  await page.goto(BASE + path);
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(1500);
  const h = await page.evaluate(() => document.documentElement.scrollHeight);
  await page.screenshot({ path: join(OUT, `${name}.jpg`), fullPage: true, type: "jpeg", quality: 85 });
  if (h > 4000) { // chat apps cap images at 8000 px: also save ≤ 3,900 px (7,800 px at 2×) slices
    for (let k = 0, y = 0; y < h; k++, y += 3900) {
      await page.screenshot({ path: join(OUT, `${name}_part${k + 1}.jpg`), fullPage: true, type: "jpeg", quality: 85,
        clip: { x: 0, y, width: WIDTH, height: Math.min(3900, h - y) } });
    }
  }
  console.log(`  saved ${name}.jpg (${h}px tall)`);
}
if (errors.length) console.log(`  page errors: ${errors.length}\n    ${errors.slice(0, 5).join("\n    ")}`);
await browser.close();
process.exit(0);
