import { test, expect, resetE2EDatabase, traceStep } from "../fixtures/db-reset";
import { LoginPage } from "../pages/LoginPage";

test.describe("PW-01: Auth, Private Middleware & Error 500/403/404", () => {
  test.beforeEach(() => {
    resetE2EDatabase("CLEAN_EMPTY");
  });

  test("enforces middleware redirect, RBAC /403, /404, and Error500View without fake fallback @allow-console-errors", async ({
    page,
  }) => {
    await traceStep(
      page,
      "STEP 1: Middleware Private Route Guard",
      "Navigate to /workspace without session cookie",
      "Redirect to /login?from=%2Fworkspace"
    );
    await page.goto("/workspace");
    await expect(page).toHaveURL(/\/login\?from=%2Fworkspace/);

    await traceStep(
      page,
      "STEP 2: Analyst Login & RBAC /403 Block",
      "Login as analyst@xscout.local -> access / -> attempt /calibration -> switch to partner",
      "Analyst allowed on /, blocked to /403 on /calibration; Partner allowed on /"
    );
    const loginPage = new LoginPage(page);
    await loginPage.loginWithCredentials("analyst@xscout.local", "Analyst2026!");
    await expect(page).toHaveURL("http://localhost:3100/");

    await page.goto("/calibration");
    await expect(page).toHaveURL(/\/403/);

    await page.context().clearCookies();
    await loginPage.loginAsPartner();
    await expect(page).toHaveURL("http://localhost:3100/");

    await traceStep(
      page,
      "STEP 3: 404 Not Found & Backend 500 Fail-Fast Guard",
      "Visit /does-not-exist -> Intercept /api/candidates** with HTTP 500 -> reload /",
      "Render 404 view then Error500View with 0 fake fallback rows"
    );
    await page.goto("/does-not-exist");
    await expect(page.getByRole("heading", { level: 2, name: /404/ })).toBeVisible();

    await page.route("**/api/candidates**", (route) =>
      route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Simulated E2E backend outage" }),
      })
    );
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 2, name: /500/ })).toBeVisible();
    await expect(page.getByTestId("candidate-row-minh_quant")).toHaveCount(0);
  });
});

