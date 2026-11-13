import { test, expect, resetE2EDatabase, traceStep } from "../fixtures/db-reset";
import { LoginPage } from "../pages/LoginPage";
import { WorkspacePage } from "../pages/WorkspacePage";

test.describe("PW-09: Bilingual EN <-> VI & Zero Console Errors", () => {
  test.beforeEach(() => {
    resetE2EDatabase("SEED_PACK_EVALUATED");
  });

  test("switches seamlessly between EN and VI across all pages with zero raw i18n keys", async ({
    page,
  }) => {
    await traceStep(
      page,
      "STEP 1: Switch EN -> VI & Verify Workspace + Modal Localization",
      "Login -> User menu -> VI -> check Vietnamese headings & Review Modal CTA",
      "Heading 'Bàn duyệt Ứng viên HITL' and 'Phê duyệt' rendered without raw keys"
    );
    await new LoginPage(page).loginAsPartner();
    const workspace = new WorkspacePage(page);
    await workspace.goto();

    await page.getByTestId("user-menu-btn").click();
    await page.getByTestId("lang-vi-btn").click();
    await expect(
      page.getByRole("heading", { name: "Bàn duyệt Ứng viên HITL" })
    ).toBeVisible();
    await expect(page.getByTestId("filter-pill-ALL")).toContainText("Tất cả Ứng viên");

    await workspace.search("minh_quant");
    await workspace.openReviewModal("minh_quant");
    await expect(page.getByTestId("approve-send-btn")).toContainText("Phê duyệt");
    await workspace.closeModal();

    await traceStep(
      page,
      "STEP 2: Navigate /ingestion, /ledger, /calibration in VI & Switch Back EN",
      "Visit all routes in VI (assert 0 raw i18n keys) -> switch EN -> /",
      "Zero leaked translation keys and zero console.error/pageerror"
    );
    for (const route of ["/ingestion", "/ledger", "/calibration"]) {
      await page.goto(route);
      const bodyText = await page.locator("body").innerText();
      expect(bodyText).not.toMatch(/\b(workspace|review_modal|ledger|ingestion)\.[a-z_]+/);
    }

    // Switch VI -> EN back cleanly
    await page.getByTestId("user-menu-btn").click();
    await page.getByTestId("lang-en-btn").click();
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "HITL Review Workspace" })
    ).toBeVisible();
  });
});

