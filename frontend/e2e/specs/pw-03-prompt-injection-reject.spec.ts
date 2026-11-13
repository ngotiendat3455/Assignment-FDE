import { test, expect, resetE2EDatabase, traceStep } from "../fixtures/db-reset";
import { LoginPage } from "../pages/LoginPage";
import { WorkspacePage } from "../pages/WorkspacePage";

test.describe("PW-03: Prompt Injection Shield & Quick Reject", () => {
  test.beforeEach(() => {
    resetE2EDatabase("SEED_PACK_EVALUATED");
  });

  test("neutralizes P017 injection draft and transitions rejected candidates cleanly", async ({
    page,
  }) => {
    await traceStep(
      page,
      "STEP 1: [E2E-02] Inspect P017 (@override_bot99) Prompt Injection Draft & Modal Reject",
      "Login -> search override_bot99 -> open Review Modal -> verify sanitized empty draft -> click modal-reject-btn",
      "draft_dm neutralized (no PWNED_BY_PROMPT_INJECTION); status transitions PENDING_REVIEW -> REJECTED"
    );
    await new LoginPage(page).loginAsPartner();
    const workspace = new WorkspacePage(page);
    await workspace.goto();

    await workspace.search("override_bot99");
    await workspace.openReviewModal("override_bot99");

    const draftValue = await page.getByTestId("dm-composer-textarea").inputValue();
    expect(draftValue).toBe("");
    expect(draftValue).not.toContain("PWNED_BY_PROMPT_INJECTION");

    await Promise.all([
      page.waitForResponse(
        (res) => res.url().includes("/reject") && res.request().method() === "POST"
      ),
      page.getByTestId("modal-reject-btn").click(),
    ]);

    await expect(page.getByTestId("candidate-status-override_bot99")).toHaveAttribute(
      "data-status",
      "REJECTED"
    );

    await traceStep(
      page,
      "STEP 2: Quick Reject P009 (@kevin_wrapper) & Filter Rejected Tab",
      "Search kevin_wrapper -> click reject-btn-kevin_wrapper -> filter REJECTED",
      "Both @override_bot99 and @kevin_wrapper appear in REJECTED state"
    );
    await workspace.search("kevin_wrapper");
    await Promise.all([
      page.waitForResponse(
        (res) => res.url().includes("/reject") && res.request().method() === "POST"
      ),
      page.getByTestId("reject-btn-kevin_wrapper").click(),
    ]);

    await workspace.search("");
    await workspace.filterBy("REJECTED");
    await expect(page.getByTestId("candidate-row-override_bot99")).toBeVisible();
    await expect(page.getByTestId("candidate-row-kevin_wrapper")).toBeVisible();
  });
});

