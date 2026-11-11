import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { execSync } from "node:child_process";

// D97: the commit this UI bundle was built from; compared with the server's commit at runtime (stale-UI banner).
function uiCommit(): string {
  const env = process.env.VITE_UI_COMMIT || process.env.GITHUB_SHA;
  if (env) return env.trim();
  try {
    return execSync("git rev-parse HEAD", { stdio: ["ignore", "pipe", "ignore"] }).toString().trim() || "dev";
  } catch {
    return "dev";
  }
}

export default defineConfig({
  plugins: [react()],
  define: { __UI_COMMIT__: JSON.stringify(uiCommit()) },
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", ws: true },
      "/ws": { target: "ws://127.0.0.1:8000", ws: true },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
