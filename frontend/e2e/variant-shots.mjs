// Style-variant screenshots (current + glass/terminal/neon/minimal): real server on a THROWAWAY scratch DB (same setup as full.mjs), serves frontend/dist.
// Usage: node frontend/e2e/ui-shots.mjs <outdir> <prefix>   (run `npm run build` first). Never touches data/paytience.db.
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
const OUT = resolve(process.argv[2] ?? join(ROOT, "docs/results/ui/variants"));

mkdirSync(OUT, { recursive: true });

const tmp = mkdtempSync(join(tmpdir(), "paytience-shots-"));
const password = randomBytes(18).toString("base64url");
const env = {
  ...process.env, PAYTIENCE_DATABASE_URL: `sqlite:///${join(tmp, "s.db")}`,
  PAYTIENCE_RULES_PATH: join(ROOT, "config/rules/lucid_daily_25k.yaml"),
  PAYTIENCE_MASTER_KEY: randomBytes(32).toString("base64url") + "=", PAYTIENCE_WEBHOOK_SECRET: randomBytes(24).toString("hex"),
  PAYTIENCE_SCHEDULER_ENABLED: "false", PAYTIENCE_ALLOW_LIVE: "false", PAYTIENCE_WEB_DIST: join(ROOT, "frontend/dist"),
  PYTHONPATH: BACKEND, CI: "1",
};
delete env.PAYTIENCE_ADMIN_PASSWORD;
const freePort = () => new Promise((ok) => { const s = createServer(); s.listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => ok(p)); }); });
execFileSync(PY, ["-m", "alembic", "upgrade", "head"], { cwd: BACKEND, env, stdio: ["ignore", "ignore", "inherit"] });
execFileSync(PY, ["-m", "app.cli", "create-admin", "e2e"], { cwd: BACKEND, env: { ...env, PAYTIENCE_ADMIN_PASSWORD: password }, stdio: ["ignore", "ignore", "inherit"] });
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
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, reducedMotion: "no-preference" });
const page = await ctx.newPage();
await page.goto(BASE + "/login");
const user = page.getByLabel("Username");
if (await user.count()) await user.fill("e2e");
await page.getByLabel("Password").fill(password);
await page.getByRole("button", { name: "Sign in" }).click();
await page.waitForURL("**/today");
await page.request.post(BASE + "/api/accounts", { data: { label: "E1", stage: "EVAL" } });
const PAGES = [["dashboard", "/dashboard"], ["strategy", "/strategy"]];
const VARIANTS = ["current", "glass", "terminal", "neon", "minimal"];
async function shoot(p, tag) {
  for (const v of VARIANTS) for (const [name, path] of PAGES) {
    await p.goto(BASE + path + `?style=${v === "current" ? "default" : v}`);
    await p.waitForLoadState("networkidle").catch(() => {});
    await p.waitForTimeout(1500);
    const w = await p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    if (w > 0) console.log(`  ! ${v} ${tag} ${name}: horizontal overflow ${w}px`);
    await p.screenshot({ path: join(OUT, `${v}_${name}${tag === "phone" ? "_phone" : ""}.png`), fullPage: true });
  }
}
await shoot(page, "desktop");
const m = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, storageState: await ctx.storageState(), reducedMotion: "no-preference" });
await shoot(await m.newPage(), "phone");
await browser.close();
process.exit(0);
