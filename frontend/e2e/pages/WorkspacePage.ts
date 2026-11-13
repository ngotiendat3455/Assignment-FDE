import { Page, expect } from "@playwright/test";

export class WorkspacePage {
  constructor(private readonly page: Page) {}

  async goto(): Promise<void> {
    await this.page.goto("/");
    await expect(this.page.getByTestId("workspace-search-input")).toBeVisible();
  }

  async processQueue(): Promise<void> {
    const [response] = await Promise.all([
      this.page.waitForResponse(
        (res) => res.url().includes("/api/queue/process") && res.request().method() === "POST"
      ),
      this.page.getByTestId("process-queue-btn").click(),
    ]);
    expect(response.status()).toBe(200);
  }

  async filterBy(tabKey: "ALL" | "MATCHES" | "PENDING_REVIEW" | "SPARSE" | "AI_FAILED" | "BLOCKED" | "SENT" | "REJECTED"): Promise<void> {
    await this.page.getByTestId(`filter-pill-${tabKey}`).click();
  }

  async search(query: string): Promise<void> {
    await this.page.getByTestId("workspace-search-input").fill(query);
  }

  async openReviewModal(handle: string): Promise<void> {
    await this.page.getByTestId(`review-btn-${handle}`).click();
    await expect(this.page.getByTestId("dm-composer-textarea")).toBeVisible();
  }

  async closeModal(): Promise<void> {
    await this.page.getByTestId("modal-close-btn").click();
    await expect(this.page.getByTestId("modal-close-btn")).toBeHidden();
  }
}

