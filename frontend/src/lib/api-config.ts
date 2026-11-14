/**
 * Resolve REST API base URL dynamically across Local Dev, Playwright E2E,
 * Docker Compose (2-port or Nginx reverse proxy), and AWS ALB multi-env deployments.
 */
export function getApiBaseUrl(): string {
  const configured = (process.env.NEXT_PUBLIC_API_BASE_URL || "").trim();
  if (configured && configured.toLowerCase() !== "auto") {
    return configured.replace(/\/+$/, "");
  }

  if (typeof window !== "undefined") {
    const { port, hostname } = window.location;
    // Behind Nginx (:80) or AWS ALB (:443 / custom domain), route /api same-origin (Zero CORS).
    if (
      !port ||
      port === "80" ||
      port === "443" ||
      (hostname !== "localhost" && hostname !== "127.0.0.1")
    ) {
      return "/api";
    }
  }

  return "http://localhost:8000/api";
}

