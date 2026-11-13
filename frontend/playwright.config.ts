import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

const repoRoot = path.resolve(__dirname, "..");

export default defineConfig({
  testDir: "./e2e/specs",
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 2 : 1,
  timeout: 45_000,
  expect: {
    timeout: 10_000,
  },
  reporter: [
    ["list"],
    ["html", { outputFolder: "playwright-report", open: "never" }],
    ["json", { outputFile: "../tests/manual/results/playwright-results.json" }],
    ["junit", { outputFile: "../tests/manual/results/playwright-junit.xml" }],
  ],
  use: {
    baseURL: "http://localhost:3100",
    locale: "en-US",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: "python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001",
      cwd: repoRoot,
      url: "http://127.0.0.1:8001/api/health",
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        ...process.env,
        ENV_FILE: path.join(repoRoot, "backend", ".env.e2e"),
        DATABASE_URL: "sqlite:///./outreach_e2e.db",
        PORT: "8001",
        HOST: "127.0.0.1",
        DISPATCH_MODE: "SANDBOX",
        TRACE_REQUESTS: "True",
        TRACE_OUTPUT_DIR: path.join(repoRoot, "tests", "manual", "results", "traces"),
        CORS_ORIGINS: "http://localhost:3100,http://127.0.0.1:3100",
        GEMINI_API_KEY: "",
        OPENAI_API_KEY: "",
        X_BEARER_TOKEN: "",
      },
    },
    {
      command: "node e2e/start-e2e-fe.mjs",
      cwd: __dirname,
      url: "http://localhost:3100/login",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});

