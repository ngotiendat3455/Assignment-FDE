import { spawn, spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(__dirname, "..");

const e2eEnv = {
  ...process.env,
  NEXT_PUBLIC_API_BASE_URL: "http://localhost:8001/api",
  BACKEND_INTERNAL_URL: "http://127.0.0.1:8001/api",
  NEXT_DIST_DIR: ".next-e2e",
};

const isWin = process.platform === "win32";
const nextBin = path.join(frontendDir, "node_modules", ".bin", isWin ? "next.cmd" : "next");

console.log("[e2e-fe] Building isolated production bundle in .next-e2e...");
const buildResult = spawnSync(nextBin, ["build"], {
  cwd: frontendDir,
  env: e2eEnv,
  stdio: "inherit",
  shell: isWin,
});

if (buildResult.status !== 0) {
  process.exit(buildResult.status ?? 1);
}

console.log("[e2e-fe] Starting isolated Next.js E2E server on http://localhost:3100...");
const server = spawn(nextBin, ["start", "-p", "3100", "-H", "localhost"], {
  cwd: frontendDir,
  env: e2eEnv,
  stdio: "inherit",
  shell: isWin,
});

const shutdown = (signal) => {
  if (!server.killed) {
    server.kill(signal);
  }
  process.exit(0);
};

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));
server.on("exit", (code) => process.exit(code ?? 0));

