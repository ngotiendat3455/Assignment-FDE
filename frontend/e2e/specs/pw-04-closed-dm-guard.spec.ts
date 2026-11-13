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
import { LedgerPage } from "../pages/LedgerPage";

test.describe("PW-04: Closed DM Guard", () => {
  test.beforeEach(() => {
    resetE2EDatabase("SEED_PACK_EVALUATED");
  });

  test("locks Send button for can_dm=false and enforces 422 -> SEND_BLOCKED", async ({
    page,
  }) => {
    await traceStep(
      page,
      "STEP 1: [E2E-03] UI Lock Check on Closed DM Profile P019 (@arjun_infer)",
      "Login -> filter BLOCKED -> open Review Modal for @arjun_infer",
      "approve-send-btn is disabled on UI because can_dm=false"
    );
    await new LoginPage(page).loginAsPartner();
    const workspace = new WorkspacePage(page);
    await workspace.goto();

    await workspace.filterBy("BLOCKED");
    await workspace.openReviewModal("arjun_infer");
    await expect(page.getByTestId("approve-send-btn")).toBeDisabled();
    await workspace.closeModal();

    await traceStep(
      page,
      "STEP 2: Backend 422 Guard -> Transition to SEND_BLOCKED & Verify Ledger OUT-104",
      "Invoke POST /api/candidates/{id}/send for @arjun_infer -> reload Workspace -> check /ledger",
      "API returns HTTP 422; @arjun_infer transitions to SEND_BLOCKED; OUT-104 stays BLOCKED"
    );
    const headers = await getPartnerAuthHeaders(page.request);
    const listRes = await page.request.get(
      `${E2E_API_BASE}/candidates?search=arjun_infer`,
      { headers }
    );
    const arjun = ((await listRes.json()) as { items: Array<{ id: number }> }).items[0];
    const sendBlockedRes = await page.request.post(
      `${E2E_API_BASE}/candidates/${arjun.id}/send`,
      { headers, data: { custom_message: "Test blocked DM" } }
    );
    expect(sendBlockedRes.status()).toBe(422);

    await page.reload();
    await workspace.filterBy("BLOCKED");
    await expect(page.getByTestId("candidate-status-arjun_infer")).toHaveAttribute(
      "data-status",
      "SEND_BLOCKED"
    );

    const ledger = new LedgerPage(page);
    await ledger.goto();
    await expect(page.getByTestId("ledger-row-OUT-104")).toHaveAttribute(
      "data-status",
      "BLOCKED"
    );
  });
});

