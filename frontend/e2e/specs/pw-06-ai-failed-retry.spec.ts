import {
  test,
  expect,
  resetE2EDatabase,
  getPartnerAuthHeaders,
  traceStep,
  E2E_API_BASE,
} from "../fixtures/db-reset";
import { LoginPage } from "../pages/LoginPage";
import { WorkspacePage } from "../pages/WorkspacePage";

test.describe("PW-06: Fault Isolation AI_FAILED & UI Retry", () => {
  test.beforeEach(() => {
    resetE2EDatabase("SEED_PACK_EVALUATED");
  });

  test("isolates LLM outage into AI_FAILED and recovers via UI Retry button", async ({
    page,
  }) => {
    await traceStep(
      page,
      "STEP 1: [E2E-05 Setup] Ingest @e2e_retry_founder with queue_ai_enabled=false & Simulate LLM Failure",
      "POST /api/ingestion/csv (queue_ai_enabled=false) -> POST /api/queue/evaluate/{id} (simulate_failure=true)",
      "Candidate enters QUEUED_FOR_AI then isolates cleanly into AI_FAILED (no fake low score)"
    );
    const headers = await getPartnerAuthHeaders(page.request);
    const csv =
      "handle,name,location,bio,recent_tweets,can_dm,segment\n" +
      '@e2e_retry_founder,Retry Builder,"Singapore","Founder building distributed Rust vector index.","[2026-11-11] Shipped SIMD PQ quantization kernel for SEA fintech search.",true,SEG-02: LLM Inference & AI Infra\n';

    const csvRes = await page.request.post(`${E2E_API_BASE}/ingestion/csv`, {
      headers,
      data: {
        csv_content: csv,
        skip_ledger_collisions: true,
        queue_ai_enabled: false,
      },
    });
    expect(csvRes.status()).toBe(200);

    const searchRes = await page.request.get(
      `${E2E_API_BASE}/candidates?search=e2e_retry_founder`,
      { headers }
    );
    const cand = ((await searchRes.json()) as { items: Array<{ id: number }> }).items[0];

    const failRes = await page.request.post(
      `${E2E_API_BASE}/queue/evaluate/${cand.id}`,
      {
        headers,
        data: { simulate_failure: true },
      }
    );
    expect(failRes.status()).toBe(200);

    await traceStep(
      page,
      "STEP 2: Verify AI_FAILED Badge, Click UI Retry & Process Queue",
      "Login -> filter AI_FAILED -> click retry-btn-e2e_retry_founder -> Process Queue",
      "Recovery transition: AI_FAILED -> QUEUED_FOR_AI -> PENDING_REVIEW"
    );
    await new LoginPage(page).loginAsPartner();
    const workspace = new WorkspacePage(page);
    await workspace.goto();
    await workspace.filterBy("AI_FAILED");

    await expect(
      page.getByTestId("candidate-status-e2e_retry_founder")
    ).toHaveAttribute("data-status", "AI_FAILED");

    await Promise.all([
      page.waitForResponse(
        (res) => res.url().includes("/retry") && res.request().method() === "POST"
      ),
      page.getByTestId("retry-btn-e2e_retry_founder").click(),
    ]);

    await workspace.filterBy("ALL");
    await workspace.processQueue();
    await workspace.search("e2e_retry_founder");

    await expect(
      page.getByTestId("candidate-status-e2e_retry_founder")
    ).toHaveAttribute("data-status", "PENDING_REVIEW");
  });
});

