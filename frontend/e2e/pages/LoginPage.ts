import { Page, expect } from "@playwright/test";

export class LoginPage {
  constructor(private readonly page: Page) {}

  async goto(fromPath?: string): Promise<void> {
    const url = fromPath ? `/login?from=${encodeURIComponent(fromPath)}` : "/login";
    await this.page.goto(url);
  }

  async loginAsPartner(): Promise<void> {
    await this.goto();
    await expect(this.page.getByTestId("login-submit")).toBeVisible();
    await Promise.all([
      this.page.waitForURL((url) => url.pathname === "/"),
      this.page.getByTestId("login-submit").click(),
    ]);
  }

  async loginWithCredentials(email: string, password: string): Promise<void> {
    await this.goto();
    await this.page.locator("#login-email").fill(email);
    await this.page.locator("#login-password").fill(password);
    await Promise.all([
      this.page.waitForURL((url) => url.pathname === "/"),
      this.page.getByTestId("login-submit").click(),
    ]);
  }
}

