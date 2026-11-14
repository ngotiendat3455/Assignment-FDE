import {
  CsvPreflightResponse,
  IngestionAuditReport,
  LiveXLookupResponse,
  SingleCandidatePayload,
} from "@/types/ingestion";
import { getApiBaseUrl } from "@/lib/api-config";

export const SAMPLE_CSV_TEMPLATE = `handle,name,location,bio,recent_tweets,can_dm,segment
@minh_quant,Minh Nguyen,"Hanoi, Vietnam","Founder @TensorEdgeVN. Building ultra-fast C++/CUDA/ARM LLM inference engine.","[2026-11-08] Just open-sourced our AWQ-W4A8 speculative decoding kernel for L40S GPUs.",true,SEG-02: LLM Inference & AI Infra
@dr_somchai_ai,Dr. Somchai Charoen,"Bangkok, Thailand","CEO @SiamAgriBot | Autonomous ROS2 laser-weeding rovers.","[2026-11-07] Field trial results: 3 autonomous rovers ran 140 hours continuously in 38C mud conditions.",true,SEG-01: SEA Embodied AI & Robotics
@ananya_vision,Ananya Wijaya,"Jakarta, Indonesia","Co-founder @NusaVisionAI. Edge VLM quality inspection for electronics assembly lines.","[2026-11-07] Deployed our 3B vision-language model on Jetson Orin Nano across 14 SMT lines in Batam.",true,SEG-01: SEA Embodied AI & Robotics
@minh_quant,Minh Nguyen Duplicate,"Hanoi, Vietnam","Duplicate row in same CSV batch to test in-batch deduplication.","[2026-11-08] Duplicate tweet row.",true,SEG-02: LLM Inference & AI Infra
@linhtran_robo,Linh Tran,"Ho Chi Minh City, Vietnam","Co-founder & CTO @MekongRobotics. Autonomous mobile manipulation for electronics factories.","[2026-11-09] Completed 30-day pilot with 12 autonomous mobile cobots.",true,SEG-01: SEA Embodied AI & Robotics`;

export function normalizeHandleClient(raw: string): string {
  const cleaned = raw.trim().replace(/^["']+|["']+$/g, "");
  const urlMatch = cleaned.match(
    /^https?:\/\/(?:www\.)?(?:x\.com|twitter\.com)\/([A-Za-z0-9_]+)/i
  );
  if (urlMatch && urlMatch[1]) {
    return urlMatch[1].toLowerCase();
  }
  return cleaned.replace(/^@+/, "").trim().toLowerCase();
}

export class ApiRequestError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
  }
}

async function handleApiResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const errData = (await res.json().catch(() => ({}))) as { detail?: string };
    const detail =
      errData.detail || `API Error: ${res.status} ${res.statusText}`;

    // Only treat 401 as an expired app session when it is NOT an upstream X API credential error.
    if (
      res.status === 401 &&
      !detail.startsWith("[X API") &&
      typeof window !== "undefined"
    ) {
      window.location.href = "/login";
      throw new ApiRequestError(401, "Unauthorized (401)");
    }

    throw new ApiRequestError(res.status, detail);
  }
  return (await res.json()) as T;
}

export async function triggerSeedPackIngest(
  segment?: string
): Promise<IngestionAuditReport> {
  const res = await fetch(`${getApiBaseUrl()}/ingestion/seed`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ segment: segment || null }),
  });
  return handleApiResponse<IngestionAuditReport>(res);
}

export async function runCsvPreflight(
  csvContent: string
): Promise<CsvPreflightResponse> {
  const res = await fetch(`${getApiBaseUrl()}/ingestion/preflight`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ csv_content: csvContent }),
  });
  return handleApiResponse<CsvPreflightResponse>(res);
}

export async function ingestCsvBatch(
  csvContent: string,
  defaultSegment?: string,
  options?: {
    skipLedgerCollisions?: boolean;
    queueAiEnabled?: boolean;
  }
): Promise<IngestionAuditReport> {
  const res = await fetch(`${getApiBaseUrl()}/ingestion/csv`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      csv_content: csvContent,
      default_segment: defaultSegment || null,
      skip_ledger_collisions: options?.skipLedgerCollisions ?? true,
      queue_ai_enabled: options?.queueAiEnabled ?? true,
    }),
  });
  return handleApiResponse<IngestionAuditReport>(res);
}

export async function lookupLiveXHandle(
  rawHandle: string
): Promise<LiveXLookupResponse> {
  const norm = normalizeHandleClient(rawHandle);
  const res = await fetch(
    `${getApiBaseUrl()}/ingestion/x-lookup?handle=${encodeURIComponent(norm)}`,
    {
      method: "GET",
      credentials: "include",
    }
  );
  return handleApiResponse<LiveXLookupResponse>(res);
}

export async function ingestSingleCandidate(
  payload: SingleCandidatePayload
): Promise<IngestionAuditReport> {
  const res = await fetch(`${getApiBaseUrl()}/ingestion/single`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return handleApiResponse<IngestionAuditReport>(res);
}
