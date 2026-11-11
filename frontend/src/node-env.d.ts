/** Minimal typings for vite.config.ts (tsc includes it; @types/node is not a dependency). */
declare const process: { env: Record<string, string | undefined> };
declare module "node:child_process" {
  export function execSync(cmd: string, opts?: { stdio?: string[] }): { toString(): string };
}
