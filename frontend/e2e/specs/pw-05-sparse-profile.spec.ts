import { test, expect, resetE2EDatabase, traceStep } from "../fixtures/db-reset";
import { LoginPage } from "../pages/LoginPage";
import { WorkspacePage } from "../pages/WorkspacePage";

test.describe("PW-05: Sparse Profile Anti-Hallucination", () => {
  test.beforeEach(() => {
    resetE2EDatabase("SEED_PACK_EVALUATED");
  });

  test("flags P018 as INSUFFICIENT_EVIDENCE with empty draft DM", async ({
    page,
  }) => {
    await traceStep(
      page,
      "STEP 1: [E2E-04] Anti-Hallucination Guard on Sparse Profile P018 (@ghost_builder_sea)",
      "Login -> filter SPARSE tab -> open Review Modal for @ghost_builder_sea",
      "Status is INSUFFICIENT_EVIDENCE and draft DM textarea is strictly empty"
    );
    await new LoginPage(page).loginAsPartner();
    const workspace = new WorkspacePage(page);
    await workspace.goto();

    await workspace.filterBy("SPARSE");
    await expect(
      page.getByTestId("candidate-status-ghost_builder_sea")
    ).toHaveAttribute("data-status", "INSUFFICIENT_EVIDENCE");

    await workspace.openReviewModal("ghost_builder_sea");
    await expect(page.getByTestId("dm-composer-textarea")).toHaveValue("");
    await workspace.closeModal();
  });
});

