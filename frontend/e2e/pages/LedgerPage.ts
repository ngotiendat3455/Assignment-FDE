import { Page, expect } from "@playwright/test";

export class LedgerPage {
  constructor(private readonly page: Page) {}

  async goto(): Promise<void> {
    await this.page.goto("/ledger");
  }

  async gotoCalibration(): Promise<void> {
    await this.page.goto("/calibration");
  }

  async openAuditDrawer(outreachId: string): Promise<void> {
    await this.page.getByTestId(`audit-btn-${outreachId}`).click();
    await expect(this.page.getByTestId("drawer-close-btn")).toBeVisible();
  }

  async closeDrawer(): Promise<void> {
    await this.page.getByTestId("drawer-close-btn").click();
    await expect(this.page.getByTestId("drawer-close-btn")).toBeHidden();
  }

  async recordReply(outreachId: string, replyText: string): Promise<void> {
    await this.page.getByTestId(`reply-btn-${outreachId}`).click();
    await this.page.getByTestId("reply-modal-textarea").fill(replyText);
    const [resp] = await Promise.all([
      this.page.waitForResponse(
        (res) => res.url().includes("/api/ledger/") && res.url().endsWith("/reply")
      ),
      this.page.getByTestId("reply-modal-save-btn").click(),
    ]);
    expect(resp.status()).toBe(200);
  }

  async markHandled(outreachId: string): Promise<void> {
    const [resp] = await Promise.all([
      this.page.waitForResponse(
        (res) => res.url().includes("/api/ledger/") && res.url().endsWith("/handled")
      ),
      this.page.getByTestId(`handled-btn-${outreachId}`).click(),
    ]);
    expect(resp.status()).toBe(200);
  }
}

