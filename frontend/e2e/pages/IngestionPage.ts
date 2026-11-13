import { Page, expect } from "@playwright/test";

export class IngestionPage {
  constructor(private readonly page: Page) {}

  async goto(): Promise<void> {
    await this.page.goto("/ingestion");
  }

  async loadSeedPack(): Promise<void> {
    await this.page.getByTestId("tab-seed").click();
    const [response] = await Promise.all([
      this.page.waitForResponse(
        (res) => res.url().includes("/api/ingestion/seed") && res.request().method() === "POST"
      ),
      this.page.getByTestId("seed-ingest-btn").click(),
    ]);
    expect(response.status()).toBe(200);
    await expect(this.page.getByTestId("ingestion-audit-card")).toBeVisible();
  }

  async switchToCsvTab(): Promise<void> {
    await this.page.getByTestId("tab-csv").click();
  }

  async uploadCsvFile(filePath: string): Promise<void> {
    await this.page.getByTestId("csv-file-input").setInputFiles(filePath);
  }

  async submitValidCsv(): Promise<void> {
    const [response] = await Promise.all([
      this.page.waitForResponse(
        (res) => res.url().includes("/api/ingestion/csv") && res.request().method() === "POST"
      ),
      this.page.getByTestId("csv-upload-btn").click(),
    ]);
    expect(response.status()).toBe(200);
    await expect(this.page.getByTestId("ingestion-audit-card")).toBeVisible();
  }

  async switchToLiveTab(): Promise<void> {
    await this.page.getByTestId("tab-live").click();
  }

  async lookupHandle(handle: string): Promise<void> {
    await this.page.getByTestId("live-lookup-input").fill(handle);
    const [response] = await Promise.all([
      this.page.waitForResponse(
        (res) => res.url().includes("/api/ingestion/x-lookup") && res.request().method() === "GET"
      ),
      this.page.getByTestId("live-lookup-submit").click(),
    ]);
    expect(response.status()).toBe(200);
  }
}

