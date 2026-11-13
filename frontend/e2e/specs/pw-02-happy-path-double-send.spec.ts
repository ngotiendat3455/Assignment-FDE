import {
  test,
  expect,
  resetE2EDatabase,
  getPartnerAuthHeaders,
  traceStep,
  E2E_API_BASE,
} from "../fixtures/db-reset";
import { LoginPage } from "../pages/LoginPage";
import { IngestionPage } from "../pages/IngestionPage";
import { WorkspacePage } from "../pages/WorkspacePage";
import { LedgerPage } from "../pages/LedgerPage";

test.describe("PW-02: Happy Path 5 States & Double-Messaging Lock", () => {
  test.beforeEach(() => {
    resetE2EDatabase("CLEAN_EMPTY");
  });

  test("completes full Seed -> Queue -> Grounded Edit -> Send -> 409 Lock -> Reply -> Handled lifecycle", async ({
    page,
  }) => {
    await traceStep(
      page,
      "STEP 1: Partner Login & [F1] 1-Click Seed Pack",
      "Login Partner -> /ingestion -> Click Load Seed Pack",
      "queued_for_ai=16, in_batch_duplicates=1, ledger_collisions=3"
    );
    const loginPage = new LoginPage(page);
    await loginPage.loginAsPartner();

    const ingestion = new IngestionPage(page);
    await ingestion.goto();
    await ingestion.loadSeedPack();
    await expect(page.getByTestId("audit-queued-count")).toHaveText("16");
    await expect(page.getByTestId("audit-duplicates-count")).toHaveText("1");
    await expect(page.getByTestId("audit-collisions-count")).toHaveText("3");

    await traceStep(
      page,
      "STEP 2: [F4/F5] Process AI Queue & Triage P002 (@minh_quant)",
      "/workspace -> Process Queue -> Search minh_quant",
      "@minh_quant moves from QUEUED_FOR_AI to PENDING_REVIEW"
    );
    const workspace = new WorkspacePage(page);
    await workspace.goto();
    await workspace.processQueue();
    await workspace.search("minh_quant");
    await expect(page.getByTestId("candidate-status-minh_quant")).toHaveAttribute(
      "data-status",
      "PENDING_REVIEW"
    );

    await traceStep(
      page,
      "STEP 3: [E2E-01 / ER-F5-F6 T1->T2] Inspect Grounded Evidence, Edit DM & Approve & Send",
      "Open Review Modal -> verify <mark> highlight -> edit DM -> Approve & Send",
      "@minh_quant transitions PENDING_REVIEW -> APPROVED_QUEUED -> SENT; OutreachLedger OUT-105 created"
    );
    await workspace.openReviewModal("minh_quant");
    await expect(page.getByTestId("evidence-highlight").first()).toBeVisible();

    const composer = page.getByTestId("dm-composer-textarea");
    const baseDraft = await composer.inputValue();
    const editedMessage = `${baseDraft} P.S. Next week in Hanoi!`;
    await composer.fill(editedMessage);

    const [sendResponse] = await Promise.all([
      page.waitForResponse(
        (res) =>
          res.url().includes("/api/candidates/") &&
          res.url().endsWith("/send") &&
          res.request().method() === "POST"
      ),
      page.getByTestId("approve-send-btn").click(),
    ]);
    expect(sendResponse.status()).toBe(200);
    const sendBody = (await sendResponse.json()) as {
      candidate: { id: number };
      ledger: { outreach_id?: string };
    };

    await expect(page.getByTestId("candidate-status-minh_quant")).toHaveAttribute(
      "data-status",
      "SENT"
    );
    await page.reload();
    await workspace.search("minh_quant");
    await expect(page.getByTestId("candidate-status-minh_quant")).toHaveAttribute(
      "data-status",
      "SENT"
    );

    await traceStep(
      page,
      "STEP 4: [Guard E2E-06] Two-Tier Zero Double-Messaging Lock",
      "Re-open @minh_quant modal (button disabled) + replay POST /send API",
      "UI Send locked + Backend returns 409 Conflict, Ledger unchanged"
    );
    await workspace.openReviewModal("minh_quant");
    await expect(page.getByTestId("approve-send-btn")).toBeDisabled();
    await workspace.closeModal();

    const headers = await getPartnerAuthHeaders(page.request);
    const dupRes = await page.request.post(
      `${E2E_API_BASE}/candidates/${sendBody.candidate.id}/send`,
      {
        headers,
        data: { custom_message: "Duplicate send attempt" },
      }
    );
    expect(dupRes.status()).toBe(409);

    await traceStep(
      page,
      "STEP 5: [ER-F5-F6 T3 / F6] Ledger OUT-105 -> Record Reply -> Mark Handled",
      "/ledger -> verify OUT-105 -> Record Reply -> Mark Handled -> reload persistence",
      "@minh_quant transitions SENT -> REPLIED; needs_attention toggles true -> false"
    );
    const ledger = new LedgerPage(page);
    await ledger.goto();
    const minhRow = page.locator('[data-testid^="ledger-row-"]', {
      hasText: "@minh_quant",
    });
    await expect(minhRow).toBeVisible();
    await expect(minhRow).toContainText("P.S. Next week in Hanoi!");

    const outTestId = await minhRow.getAttribute("data-testid");
    const outreachId = outTestId!.replace("ledger-row-", "");
    expect(outreachId).toBe("OUT-105");

    await ledger.recordReply(outreachId, "Sure, let's chat Tuesday in Hanoi!");
    await expect(page.getByTestId(`needs-attention-badge-${outreachId}`)).toBeVisible();
    await expect(minhRow).toHaveAttribute("data-status", "REPLIED");

    await ledger.markHandled(outreachId);
    await expect(page.getByTestId(`needs-attention-badge-${outreachId}`)).toHaveCount(0);
    await expect(minhRow).toHaveAttribute("data-status", "REPLIED");

    await page.reload();
    await expect(page.getByTestId(`ledger-row-${outreachId}`)).toHaveAttribute(
      "data-status",
      "REPLIED"
    );
  });
});

