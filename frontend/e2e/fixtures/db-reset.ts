import { test as base, expect, Page, request as playwrightRequest } from "@playwright/test";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

export type E2EPreset = "CLEAN_EMPTY" | "SEED_PACK_EVALUATED";

export const E2E_API_BASE = "http://127.0.0.1:8001/api";
export const REPO_ROOT = path.resolve(__dirname, "..", "..", "..");
export const TRACE_OUTPUT_DIR = path.join(REPO_ROOT, "tests", "manual", "results", "traces");

interface FlowCatalogEntry {
  flowRef: string;
  title: string;
  expectedStates: string[];
  forbidden: string[];
}

const PW_FLOW_CATALOG: Record<string, FlowCatalogEntry> = {
  "PW-01": {
    flowRef: "Feature 03 (Auth, Middleware RBAC & ErrorViews 403/404/500)",
    title: "Enforce Middleware /login redirect, Analyst -> /403, /404, and Error500View without fake fallback",
    expectedStates: [],
    forbidden: ["Unauthenticated ↛ Private Page", "Analyst ↛ /calibration", "500 Outage ↛ Fake Fallback Data"],
  },
  "PW-02": {
    flowRef: "testing/e2e.md: E2E-01 + E2E-06 | ER-F5-F6 (T1..T4)",
    title: "Happy Path Full Lifecycle (Seed -> Queue -> Grounded Edit -> Send -> 409 Lock -> Reply -> Handled)",
    expectedStates: ["QUEUED_FOR_AI", "PENDING_REVIEW", "APPROVED_QUEUED", "SENT", "REPLIED"],
    forbidden: ["SENT ↛ SENT (409 Conflict Zero Double-Messaging)"],
  },
  "PW-03": {
    flowRef: "testing/e2e.md: E2E-02 (Prompt Injection Shield P017 + Quick Reject P009)",
    title: "Neutralize P017 prompt injection draft & transition rejected candidates cleanly",
    expectedStates: ["PENDING_REVIEW", "REJECTED"],
    forbidden: ["P017 ↛ Leaked PWNED_BY_PROMPT_INJECTION"],
  },
  "PW-04": {
    flowRef: "testing/e2e.md: E2E-03 (Closed DM Guard P019)",
    title: "Lock Send button on UI for can_dm=false & enforce 422 -> SEND_BLOCKED + Ledger BLOCKED",
    expectedStates: ["PENDING_REVIEW", "APPROVED_QUEUED", "SEND_BLOCKED"],
    forbidden: ["can_dm=false ↛ SENT (422 Unprocessable Entity)"],
  },
  "PW-05": {
    flowRef: "testing/e2e.md: E2E-04 (Sparse Profile Anti-Hallucination P018)",
    title: "Flag sparse profile P018 as INSUFFICIENT_EVIDENCE with empty draft_dm & disabled Send",
    expectedStates: ["QUEUED_FOR_AI", "INSUFFICIENT_EVIDENCE"],
    forbidden: ["Sparse Profile ↛ Hallucinated DM"],
  },
  "PW-06": {
    flowRef: "testing/e2e.md: E2E-05 (Fault Isolation AI_FAILED & UI Retry)",
    title: "Isolate LLM failure into AI_FAILED & recover cleanly via UI Retry button -> PENDING_REVIEW",
    expectedStates: ["QUEUED_FOR_AI", "AI_FAILED", "PENDING_REVIEW"],
    forbidden: ["LLM 503 Outage ↛ Fake Low Score"],
  },
  "PW-07": {
    flowRef: "testing/e2e.md: E2E-07 | ER-data-packing.md (Batch T1..T3 + Live X Lookup)",
    title: "Pre-flight CSV error guard, Cross-Batch Dedup without regressing REPLIED, & Live X Lookup locks",
    expectedStates: ["QUEUED_FOR_AI", "REPLIED"],
    forbidden: ["REPLIED ↛ QUEUED_FOR_AI", "In-Batch Duplicate ↛ Extra Candidate Row"],
  },
  "PW-08": {
    flowRef: "testing/e2e.md: E2E-08 (Ledger Audit Trail, 422 Reply Guard & Calibration Matrix)",
    title: "Verify Ledger Filter Pills, Audit Drawer OUT-101, 422 reply block on OUT-104, and 100% Calibration Matrix",
    expectedStates: ["REPLIED", "SENT", "SEND_BLOCKED"],
    forbidden: ["BLOCKED OUT-104 ↛ REPLIED (422 Unprocessable Entity)"],
  },
  "PW-09": {
    flowRef: "Feature 00 & UX Parity (Bilingual EN <-> VI + Zero Console Errors)",
    title: "Switch EN <-> VI cleanly across Workspace, Modal, Ingestion, Ledger & Calibration with 0 leaked keys",
    expectedStates: ["PENDING_REVIEW", "SENT", "REPLIED"],
    forbidden: ["Translated Page ↛ Raw i18n Keys / Console Errors"],
  },
};

const _startedTests = new Set<string>();

function resolveTestCaseId(titlePath: string[]): string {
  const joined = titlePath.join(" ");
  const pwMatch = joined.match(/PW-\d{2}/);
  if (pwMatch) return pwMatch[0];
  return joined.replace(/[^A-Za-z0-9_.-]+/g, "_").slice(0, 64) || "e2e_test";
}

function setActiveMarkerOnly(testCaseId: string): void {
  fs.mkdirSync(TRACE_OUTPUT_DIR, { recursive: true });
  fs.writeFileSync(path.join(TRACE_OUTPUT_DIR, ".active-testcase"), testCaseId, "utf-8");
}

async function postTraceSafe(endpoint: string, data: Record<string, unknown>): Promise<void> {
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const apiCtx = await playwrightRequest.newContext();
    try {
      await apiCtx.post(`${E2E_API_BASE}${endpoint}`, { data });
      return;
    } catch {
      if (attempt === 1) return;
    } finally {
      await apiCtx.dispose();
    }
  }
}

async function ensureFlowStarted(_page: Page, testCaseId: string): Promise<void> {
  if (_startedTests.has(testCaseId)) return;
  _startedTests.add(testCaseId);
  const meta = PW_FLOW_CATALOG[testCaseId] ?? {
    flowRef: testCaseId,
    title: testCaseId,
    expectedStates: [],
    forbidden: [],
  };
  await postTraceSafe("/_trace/session", {
    testcase_id: testCaseId,
    flow_ref: meta.flowRef,
    title: meta.title,
    expected_states: meta.expectedStates,
    forbidden_transitions: meta.forbidden,
    reset_file: true,
  });
}

export async function traceStep(
  page: Page,
  step: string,
  uiAction = "",
  expected = ""
): Promise<void> {
  const markerPath = path.join(TRACE_OUTPUT_DIR, ".active-testcase");
  const testCaseId = fs.existsSync(markerPath)
    ? fs.readFileSync(markerPath, "utf-8").trim() || "unassigned"
    : "unassigned";
  await ensureFlowStarted(page, testCaseId);
  await postTraceSafe("/_trace/step", {
    testcase_id: testCaseId,
    step,
    ui_action: uiAction,
    expected,
    include_db_snapshot: true,
  });
}

export async function getPartnerAuthHeaders(
  _request?: Page["request"]
): Promise<Record<string, string>> {
  const apiCtx = await playwrightRequest.newContext();
  try {
    const markerPath = path.join(TRACE_OUTPUT_DIR, ".active-testcase");
    const activeTc = fs.existsSync(markerPath)
      ? fs.readFileSync(markerPath, "utf-8").trim()
      : "";
    const loginRes = await apiCtx.post(`${E2E_API_BASE}/auth/demo-login`, {
      headers: activeTc ? { "X-Test-Case-Id": activeTc } : undefined,
    });
    expect(loginRes.status()).toBe(200);
    const body = (await loginRes.json()) as { access_token: string };
    return {
      Authorization: `Bearer ${body.access_token}`,
      ...(activeTc ? { "X-Test-Case-Id": activeTc } : {}),
    };
  } finally {
    await apiCtx.dispose();
  }
}

export function resetE2EDatabase(preset: E2EPreset): void {
  const seedScript = path.join(REPO_ROOT, "backend", "tests", "e2e_seed.py");
  execFileSync("python", [seedScript, "--preset", preset], {
    cwd: REPO_ROOT,
    env: {
      ...process.env,
      ENV_FILE: path.join(REPO_ROOT, "backend", ".env.e2e"),
      DATABASE_URL: "sqlite:///./outreach_e2e.db",
      DISPATCH_MODE: "SANDBOX",
      GEMINI_API_KEY: "",
      OPENAI_API_KEY: "",
      X_BEARER_TOKEN: "",
    },
    stdio: "pipe",
  });
}

export interface ErrorMonitor {
  consoleErrors: string[];
  pageErrors: string[];
}

export function attachErrorMonitor(page: Page): ErrorMonitor {
  const monitor: ErrorMonitor = {
    consoleErrors: [],
    pageErrors: [],
  };
  page.on("pageerror", (err) => {
    monitor.pageErrors.push(err.message);
  });
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      monitor.consoleErrors.push(msg.text());
    }
  });
  return monitor;
}

export const test = base.extend<{
  errorMonitor: ErrorMonitor;
}>({
  errorMonitor: [
    async ({ page }, use, testInfo) => {
      const testCaseId = resolveTestCaseId(testInfo.titlePath);
      _startedTests.delete(testCaseId);
      setActiveMarkerOnly(testCaseId);
      await page.setExtraHTTPHeaders({ "X-Test-Case-Id": testCaseId });

      const monitor = attachErrorMonitor(page);
      try {
        await use(monitor);
        const skipErrorCheck = testInfo.title.includes("@allow-console-errors");
        if (!skipErrorCheck) {
          expect(monitor.pageErrors, "Expected zero uncaught pageerrors").toEqual([]);
          expect(monitor.consoleErrors, "Expected zero console.error messages").toEqual([]);
        }
      } finally {
        await ensureFlowStarted(page, testCaseId).catch(() => {});
        const outcome = testInfo.status === "passed" ? "PASSED" : (testInfo.status || "FAILED").toUpperCase();
        await postTraceSafe("/_trace/finish", {
          testcase_id: testCaseId,
          status: outcome,
          notes: testInfo.error?.message ? `Error: ${testInfo.error.message}` : "",
        });
      }
    },
    { auto: true },
  ],
});

export { expect };
