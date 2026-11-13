import {
  test,
  expect,
  resetE2EDatabase,
  getPartnerAuthHeaders,
  traceStep,
  E2E_API_BASE,
} from "../fixtures/db-reset";
import { LoginPage } from "../pages/LoginPage";
import { LedgerPage } from "../pages/LedgerPage";

test.describe("PW-08: Ledger Audit Trail, 422 Guard & Calibration Matrix", () => {
  test.beforeEach(() => {
    resetE2EDatabase("SEED_PACK_EVALUATED");
  });

  test("verifies filter pills, Audit Drawer metadata, 422 reply block on OUT-104, and 100% Calibration Matrix", async ({
    page,
  }) => {
    await traceStep(
      page,
      "STEP 1: [F6] Ledger Filter Pills & Audit Drawer Metadata (OUT-101)",
      "Login -> /ledger -> filter needs_attention -> open Audit Drawer OUT-101",
      "OUT-101 visible under Needs Attention; Drawer displays idempotency key hist-OUT-101"
    );
    await new LoginPage(page).loginAsPartner();
    const ledger = new LedgerPage(page);
    await ledger.goto();

    await page.getByTestId("tab-needs_attention").click();
    await expect(page.getByTestId("ledger-row-OUT-101")).toBeVisible();
    await page.getByTestId("tab-all").click();

    await ledger.openAuditDrawer("OUT-101");
    await expect(page.getByText("hist-OUT-101")).toBeVisible();
    await ledger.closeDrawer();

    await traceStep(
      page,
      "STEP 2: [E2E-08 Guard] Block Reply on Closed/Blocked Ledger Entry OUT-104",
      "POST /api/ledger/{out104.id}/reply",
      "Backend enforces HTTP 422 Unprocessable Entity (SEND_BLOCKED ↛ REPLIED)"
    );
    const headers = await getPartnerAuthHeaders(page.request);
    const ledgerRes = await page.request.get(`${E2E_API_BASE}/ledger`, { headers });
    const entries = (
      (await ledgerRes.json()) as {
        items: Array<{ id: number; outreach_id: string }>;
      }
    ).items;
    const out104 = entries.find((e) => e.outreach_id === "OUT-104")!;
    const replyBlockedRes = await page.request.post(
      `${E2E_API_BASE}/ledger/${out104.id}/reply`,
      { headers, data: { reply_text: "Forbidden reply", needs_attention: true } }
    );
    expect(replyBlockedRes.status()).toBe(422);

    await traceStep(
      page,
      "STEP 3: [E2E-08 / ER-F5-F6 T4] Verify Partner Calibration Matrix Benchmark",
      "Navigate to /calibration",
      "Alignment accuracy KPI = 100% and edge traps P017 & P018 present"
    );
    await ledger.gotoCalibration();
    await expect(page.getByTestId("alignment-accuracy-kpi")).toContainText("100%");
    await expect(page.getByText("P017")).toBeVisible();
    await expect(page.getByText("P018")).toBeVisible();
  });
});

