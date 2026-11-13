import path from "node:path";
import { test, expect, resetE2EDatabase, traceStep } from "../fixtures/db-reset";
import { LoginPage } from "../pages/LoginPage";
import { IngestionPage } from "../pages/IngestionPage";
import { WorkspacePage } from "../pages/WorkspacePage";

const CSV_FIXTURES_DIR = path.resolve(__dirname, "..", "fixtures", "csv");

test.describe("PW-07: Cross-Batch CSV Dedup, Pre-flight & Live X Lookup", () => {
  test.beforeEach(() => {
    resetE2EDatabase("SEED_PACK_EVALUATED");
  });

  test("validates preflight error, deduplicates cross-batch CSV without regressing REPLIED, and guards Live Lookup", async ({
    page,
  }) => {
    await traceStep(
      page,
      "STEP 1: [ER-data-packing] CSV Pre-flight Validation on Missing Column",
      "/ingestion Tab 2 -> Upload missing_bio.csv",
      "preflight-error-banner shown and csv-upload-btn disabled"
    );
    await new LoginPage(page).loginAsPartner();
    const ingestion = new IngestionPage(page);
    await ingestion.goto();

    await ingestion.switchToCsvTab();
    await ingestion.uploadCsvFile(path.join(CSV_FIXTURES_DIR, "missing_bio.csv"));
    await expect(page.getByTestId("preflight-error-banner")).toBeVisible();
    await expect(page.getByTestId("csv-upload-btn")).toBeDisabled();

    await traceStep(
      page,
      "STEP 2: [E2E-07] Cross-Batch CSV Dedup & No-Regression Check on REPLIED",
      "Upload cross_batch_dedup.csv (new + in-batch dup + @linhtran_robo) -> inspect audit counts -> check Workspace",
      "queued=1, in_batch_dup=1, ledger_collision=1; @linhtran_robo stays REPLIED (never regressed to QUEUED_FOR_AI)"
    );
    await ingestion.uploadCsvFile(path.join(CSV_FIXTURES_DIR, "cross_batch_dedup.csv"));
    await expect(page.getByTestId("csv-upload-btn")).toBeEnabled();
    await ingestion.submitValidCsv();

    await expect(page.getByTestId("audit-queued-count")).toHaveText("1");
    await expect(page.getByTestId("audit-duplicates-count")).toHaveText("1");
    await expect(page.getByTestId("audit-collisions-count")).toHaveText("1");

    const workspace = new WorkspacePage(page);
    await workspace.goto();
    await workspace.search("linhtran_robo");
    await expect(page.getByTestId("candidate-status-linhtran_robo")).toHaveAttribute(
      "data-status",
      "REPLIED"
    );

    await traceStep(
      page,
      "STEP 3: [F1 Tab 3] Live X Lookup Closed DM & Already Contacted Guards",
      "/ingestion Tab 3 -> lookup @arjun_infer -> lookup @linhtran_robo",
      "DMs Closed badge for @arjun_infer; Already Contacted + live-ingest-btn disabled for @linhtran_robo"
    );
    await ingestion.goto();
    await ingestion.switchToLiveTab();
    await ingestion.lookupHandle("@arjun_infer");
    await expect(page.getByText(/DMs Closed/i)).toBeVisible();

    await ingestion.lookupHandle("@linhtran_robo");
    await expect(page.getByText(/Protected:\s*Already contacted/i)).toBeVisible();
    await expect(page.getByTestId("live-ingest-btn")).toBeDisabled();
  });
});

