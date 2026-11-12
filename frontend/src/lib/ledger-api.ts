import {
  CalibrationMatrixResponse,
  LedgerEntryItem,
  LedgerFilterTab,
  LedgerListResponse,
} from "@/types/ledger";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";

async function handleApiResponse<T>(res: Response): Promise<T> {
  if (res.status === 401 && typeof window !== "undefined") {
    window.location.href = "/login";
    throw new Error("Unauthorized (401)");
  }
  if (!res.ok) {
    const errData = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(
      errData.detail || `API Error: ${res.status} ${res.statusText}`
    );
  }
  return (await res.json()) as T;
}

export async function fetchLedgerEntries(params?: {
  filter_tab?: LedgerFilterTab;
  search?: string;
}): Promise<LedgerListResponse> {
  const query = new URLSearchParams();
  if (params?.filter_tab && params.filter_tab !== "all") {
    query.set("filter_tab", params.filter_tab);
  }
  if (params?.search && params.search.trim()) {
    query.set("search", params.search.trim());
  }

  const url = `${API_BASE_URL}/ledger${query.toString() ? `?${query.toString()}` : ""}`;
  const res = await fetch(url, {
    method: "GET",
    credentials: "include",
    headers: { Accept: "application/json" },
  });
  return handleApiResponse<LedgerListResponse>(res);
}

export async function recordLedgerReply(
  ledgerId: number,
  replyText: string,
  needsAttention: boolean = true
): Promise<{ action: string; ledger: LedgerEntryItem }> {
  const res = await fetch(`${API_BASE_URL}/ledger/${ledgerId}/reply`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      reply_text: replyText,
      needs_attention: needsAttention,
    }),
  });
  return handleApiResponse<{ action: string; ledger: LedgerEntryItem }>(res);
}

export async function markLedgerHandled(
  ledgerId: number
): Promise<{ action: string; ledger: LedgerEntryItem }> {
  const res = await fetch(`${API_BASE_URL}/ledger/${ledgerId}/handled`, {
    method: "POST",
    credentials: "include",
  });
  return handleApiResponse<{ action: string; ledger: LedgerEntryItem }>(res);
}

export async function fetchCalibrationMatrix(): Promise<CalibrationMatrixResponse> {
  const res = await fetch(`${API_BASE_URL}/ledger/calibration`, {
    method: "GET",
    credentials: "include",
    headers: { Accept: "application/json" },
  });
  return handleApiResponse<CalibrationMatrixResponse>(res);
}

