import {
  CandidateItem,
  CandidateListResponse,
  StateMachineSummary,
  SendCandidatePayload,
  SendCandidateResponse,
} from "@/types/candidate";
import { getApiBaseUrl } from "@/lib/api-config";

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

export async function fetchCandidates(params?: {
  status?: string;
  search?: string;
  min_score?: number;
}): Promise<CandidateListResponse> {
  const query = new URLSearchParams();
  if (params?.status && params.status.toUpperCase() !== "ALL") {
    query.set("status", params.status.toUpperCase());
  }
  if (params?.search && params.search.trim()) {
    query.set("search", params.search.trim());
  }
  if (params?.min_score !== undefined && params.min_score !== null) {
    query.set("min_score", String(params.min_score));
  }

  const url = `${getApiBaseUrl()}/candidates${query.toString() ? `?${query.toString()}` : ""}`;
  const res = await fetch(url, {
    method: "GET",
    credentials: "include",
    headers: {
      Accept: "application/json",
    },
  });
  return handleApiResponse<CandidateListResponse>(res);
}

export async function fetchCandidateDetail(id: number): Promise<CandidateItem> {
  const res = await fetch(`${getApiBaseUrl()}/candidates/${id}`, {
    method: "GET",
    credentials: "include",
  });
  return handleApiResponse<CandidateItem>(res);
}

export async function fetchStateMachineSummary(): Promise<StateMachineSummary> {
  const res = await fetch(`${getApiBaseUrl()}/candidates/state-summary`, {
    method: "GET",
    credentials: "include",
  });
  return handleApiResponse<StateMachineSummary>(res);
}

export async function sendCandidateDm(
  candidateId: number,
  payload: SendCandidatePayload
): Promise<SendCandidateResponse> {
  const res = await fetch(`${getApiBaseUrl()}/candidates/${candidateId}/send`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      custom_message: payload.custom_message || null,
      idempotency_key: payload.idempotency_key || null,
      dispatch_mode: payload.dispatch_mode || "SANDBOX",
    }),
  });
  return handleApiResponse<SendCandidateResponse>(res);
}

export async function rejectCandidate(
  candidateId: number,
  reason?: string
): Promise<CandidateItem> {
  const res = await fetch(`${getApiBaseUrl()}/candidates/${candidateId}/reject`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason: reason || "Manual reject by partner" }),
  });
  return handleApiResponse<CandidateItem>(res);
}

export async function retryCandidateEvaluation(
  candidateId: number
): Promise<CandidateItem> {
  const res = await fetch(`${getApiBaseUrl()}/candidates/${candidateId}/retry`, {
    method: "POST",
    credentials: "include",
  });
  return handleApiResponse<CandidateItem>(res);
}

export async function regenerateAiEvaluation(
  candidateId: number
): Promise<{ candidate: CandidateItem; evaluation: unknown }> {
  const res = await fetch(`${getApiBaseUrl()}/queue/evaluate/${candidateId}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ simulate_failure: false }),
  });
  return handleApiResponse<{ candidate: CandidateItem; evaluation: unknown }>(
    res
  );
}

