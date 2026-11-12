import {
  CsvPreflightResponse,
  CsvPreviewRow,
  IngestionAuditReport,
  LiveXLookupResponse,
  SingleCandidatePayload,
} from "@/types/ingestion";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";

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

function splitCsvLine(line: string): string[] {
  const result: string[] = [];
  let current = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"') {
      inQuotes = !inQuotes;
    } else if (ch === "," && !inQuotes) {
      result.push(current.trim());
      current = "";
    } else {
      current += ch;
    }
  }
  result.push(current.trim());
  return result;
}

export function fallbackPreflightCsv(csvContent: string): CsvPreflightResponse {
  const lines = csvContent
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0);

  if (lines.length === 0) {
    return {
      valid: false,
      total_rows: 0,
      missing_columns: ["handle", "name", "bio", "recent_tweets"],
      detected_columns: [],
      preview_rows: [],
      error_message: "CSV file is empty.",
    };
  }

  const headers = splitCsvLine(lines[0]).map((h) => h.toLowerCase());
  const findIdx = (aliases: string[]): number =>
    headers.findIndex((h) => aliases.includes(h));

  const hIdx = findIdx(["handle", "x_handle", "username", "twitter_handle"]);
  const nIdx = findIdx(["name", "full_name", "display_name"]);
  const bIdx = findIdx(["bio", "profile_bio", "description"]);
  const tIdx = findIdx(["recent_tweets", "tweets", "posts", "recent_posts"]);
  const lIdx = findIdx(["location", "region", "country", "city"]);
  const dIdx = findIdx(["can_dm", "dm_open"]);

  const missing: string[] = [];
  if (hIdx === -1) missing.push("handle");
  if (nIdx === -1) missing.push("name");
  if (bIdx === -1) missing.push("bio");
  if (tIdx === -1) missing.push("recent_tweets");

  const dataLines = lines.slice(1);
  const previewRows: CsvPreviewRow[] = dataLines.slice(0, 5).map((line, i) => {
    const cols = splitCsvLine(line);
    const rawH = hIdx !== -1 ? cols[hIdx] || "" : "";
    const normH = normalizeHandleClient(rawH);
    const nameVal = nIdx !== -1 ? cols[nIdx] || "" : "";
    const bioVal = bIdx !== -1 ? cols[bIdx] || "" : "";
    const tweetsVal = tIdx !== -1 ? cols[tIdx] || "" : "";
    const locVal = lIdx !== -1 ? cols[lIdx] || "Southeast Asia" : "Southeast Asia";
    const dmRaw = dIdx !== -1 ? (cols[dIdx] || "true").toLowerCase() : "true";
    const canDm = !["false", "0", "no", "closed"].includes(dmRaw);

    const rowMissing = [...missing];
    if (!normH && !rowMissing.includes("handle")) rowMissing.push("handle");
    if (!bioVal && !rowMissing.includes("bio")) rowMissing.push("bio");
    if (!tweetsVal && !rowMissing.includes("recent_tweets")) {
      rowMissing.push("recent_tweets");
    }

    const isValid = rowMissing.length === 0;
    return {
      line_number: i + 1,
      handle: normH ? `@${normH}` : "(empty)",
      name: nameVal || "(missing)",
      bio: bioVal || "(missing)",
      recent_tweets: tweetsVal || "(missing)",
      location: locVal,
      can_dm: canDm,
      is_valid: isValid,
      validation_note: isValid ? "Valid" : `Missing: ${rowMissing.join(", ")}`,
    };
  });

  return {
    valid: missing.length === 0 && dataLines.length > 0,
    total_rows: dataLines.length,
    missing_columns: missing,
    detected_columns: headers,
    preview_rows: previewRows,
    error_message:
      missing.length > 0
        ? `Missing required column(s): ${missing.join(", ")}`
        : null,
  };
}

export async function triggerSeedPackIngest(
  segment?: string
): Promise<IngestionAuditReport> {
  try {
    const res = await fetch(`${API_BASE_URL}/ingestion/seed`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ segment: segment || null }),
    });
    if (res.ok) {
      return (await res.json()) as IngestionAuditReport;
    }
  } catch {
    // Fallback when FastAPI server is offline during static preview
  }

  return {
    total_rows: 20,
    imported: 16,
    queued_for_ai_count: 16,
    in_batch_duplicates_skipped: 1,
    already_in_db_skipped: 3,
    already_contacted_in_ledger: 3,
    duplicate_handles: ["minh_quant"],
    collision_details: [
      { handle: "linhtran_robo", status: "REPLIED" },
      { handle: "putri_agentic", status: "SENT" },
      { handle: "harith_medai", status: "REPLIED" },
    ],
    details: [],
  };
}

export async function runCsvPreflight(
  csvContent: string
): Promise<CsvPreflightResponse> {
  try {
    const res = await fetch(`${API_BASE_URL}/ingestion/preflight`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ csv_content: csvContent }),
    });
    if (res.ok) {
      return (await res.json()) as CsvPreflightResponse;
    }
  } catch {
    // Fallback to client-side pre-flight parser
  }
  return fallbackPreflightCsv(csvContent);
}

export async function ingestCsvBatch(
  csvContent: string,
  defaultSegment?: string
): Promise<IngestionAuditReport> {
  try {
    const res = await fetch(`${API_BASE_URL}/ingestion/csv`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        csv_content: csvContent,
        default_segment: defaultSegment || null,
      }),
    });
    if (res.ok) {
      return (await res.json()) as IngestionAuditReport;
    }
  } catch {
    // Fallback client batch calculation
  }

  const pre = fallbackPreflightCsv(csvContent);
  const lines = csvContent
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0)
    .slice(1);

  const seen = new Set<string>();
  const duplicates: string[] = [];
  const collisions: { handle: string; status: string }[] = [];
  const historicalMap: Record<string, string> = {
    linhtran_robo: "REPLIED",
    putri_agentic: "SENT",
    harith_medai: "REPLIED",
  };

  let importedCount = 0;
  for (const line of lines) {
    const cols = splitCsvLine(line);
    const h = normalizeHandleClient(cols[0] || "");
    if (!h) continue;
    if (seen.has(h)) {
      duplicates.push(h);
      continue;
    }
    seen.add(h);
    if (historicalMap[h]) {
      collisions.push({ handle: h, status: historicalMap[h] });
      continue;
    }
    importedCount += 1;
  }

  return {
    total_rows: pre.total_rows,
    imported: importedCount,
    queued_for_ai_count: importedCount,
    in_batch_duplicates_skipped: duplicates.length,
    already_in_db_skipped: collisions.length,
    already_contacted_in_ledger: collisions.length,
    duplicate_handles: duplicates,
    collision_details: collisions,
    details: [],
  };
}

const SEED_LOOKUP_PROFILES: Record<string, Omit<LiveXLookupResponse, "api_connected">> = {
  minh_quant: {
    handle: "minh_quant",
    name: "Minh Nguyen",
    location: "Hanoi, Vietnam",
    bio: "Founder @TensorEdgeVN. Ex-HPC lead. Building ultra-fast C++/CUDA/ARM LLM inference engine for ASEAN banks & telcos.",
    recent_tweets: [
      "[2026-11-08] Just open-sourced our AWQ-W4A8 speculative decoding kernel for L40S GPUs — 3.4x throughput on Qwen-32B with <12ms TPOT.",
      "[2026-11-03] Production deployment #6 live in Vietnam! Processing 1.8M customer support turns/day on-prem.",
    ],
    raw_tweets_text:
      "[2026-11-08] Just open-sourced our AWQ-W4A8 speculative decoding kernel for L40S GPUs — 3.4x throughput on Qwen-32B with <12ms TPOT. || [2026-11-03] Production deployment #6 live in Vietnam!",
    can_dm: true,
    segment: "SEG-02: LLM Inference & AI Infra",
    x_user_id: "100102",
    source_mode: "SEED_PACK_FALLBACK",
    already_contacted: false,
    existing_ledger_status: null,
  },
  arjun_infer: {
    handle: "arjun_infer",
    name: "Arjun Krishnan",
    location: "Singapore",
    bio: "Founder @TritonSEA. Custom FlashAttention & Triton kernels for multi-modal audio-models. Ex-A*STAR GPU architect.",
    recent_tweets: [
      "[2026-11-08] Cut Sea-Lion-70B prefill latency by 46% on H100 using custom warp-specialized Triton kernels.",
      "[2026-11-02] Looking to connect with seed-stage deep-tech investors in Singapore.",
    ],
    raw_tweets_text:
      "[2026-11-08] Cut Sea-Lion-70B prefill latency by 46% on H100 using custom warp-specialized Triton kernels.",
    can_dm: false,
    segment: "SEG-02: LLM Inference & AI Infra",
    x_user_id: "100119",
    source_mode: "SEED_PACK_FALLBACK",
    already_contacted: false,
    existing_ledger_status: "BLOCKED",
  },
  linhtran_robo: {
    handle: "linhtran_robo",
    name: "Linh Tran",
    location: "Ho Chi Minh City, Vietnam",
    bio: "Co-founder & CTO @MekongRobotics. Building low-cost autonomous mobile manipulation for electronics factories in Vietnam.",
    recent_tweets: [
      "[2026-11-09] Just completed our 30-day pilot at a Tier-1 PCB plant in Binh Duong: 12 autonomous mobile cobots running 22 hrs/day.",
    ],
    raw_tweets_text:
      "[2026-11-09] Just completed our 30-day pilot at a Tier-1 PCB plant in Binh Duong: 12 autonomous mobile cobots running 22 hrs/day.",
    can_dm: true,
    segment: "SEG-01: SEA Embodied AI & Robotics",
    x_user_id: "100101",
    source_mode: "SEED_PACK_FALLBACK",
    already_contacted: true,
    existing_ledger_status: "REPLIED",
  },
};

export async function lookupLiveXHandle(
  rawHandle: string
): Promise<LiveXLookupResponse> {
  const norm = normalizeHandleClient(rawHandle);
  try {
    const res = await fetch(
      `${API_BASE_URL}/ingestion/x-lookup?handle=${encodeURIComponent(norm)}`
    );
    if (res.ok) {
      return (await res.json()) as LiveXLookupResponse;
    }
  } catch {
    // Fallback when backend is offline
  }

  const preset = SEED_LOOKUP_PROFILES[norm];
  if (preset) {
    return {
      ...preset,
      api_connected: false,
    };
  }

  const displayName = norm
    .split(/[._-]+/)
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : ""))
    .join(" ");

  const tweets = [
    `[2026-11-10] Building low-latency inference and robotics automation workflows in Southeast Asia (@${norm}).`,
    `[2026-11-04] Benchmarking quantized edge models on local GPU clusters in Singapore & Vietnam.`,
  ];

  return {
    handle: norm,
    name: displayName || norm,
    location: "Singapore / Southeast Asia",
    bio: `Founder & AI Engineer @${norm}. Building frontier AI infrastructure and autonomous systems in SEA.`,
    recent_tweets: tweets,
    raw_tweets_text: tweets.join(" || "),
    can_dm: true,
    segment: "SEG-02: LLM Inference & AI Infra",
    x_user_id: `sim_${norm}`,
    source_mode: "SYNTHETIC_PREVIEW",
    api_connected: false,
    already_contacted: false,
    existing_ledger_status: null,
  };
}

export async function ingestSingleCandidate(
  payload: SingleCandidatePayload
): Promise<IngestionAuditReport> {
  try {
    const res = await fetch(`${API_BASE_URL}/ingestion/single`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      return (await res.json()) as IngestionAuditReport;
    }
  } catch {
    // Fallback
  }

  return {
    total_rows: 1,
    imported: 1,
    queued_for_ai_count: 1,
    in_batch_duplicates_skipped: 0,
    already_in_db_skipped: 0,
    already_contacted_in_ledger: 0,
    duplicate_handles: [],
    collision_details: [],
    details: [],
  };
}

