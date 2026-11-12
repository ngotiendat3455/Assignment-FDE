export interface CsvPreviewRow {
  line_number: number;
  handle: string;
  name: string;
  bio: string;
  recent_tweets: string;
  location: string;
  can_dm: boolean;
  is_valid: boolean;
  validation_note: string;
}

export interface CsvPreflightResponse {
  valid: boolean;
  total_rows: number;
  missing_columns: string[];
  detected_columns: string[];
  preview_rows: CsvPreviewRow[];
  error_message?: string | null;
}

export interface CollisionDetail {
  handle: string;
  status: string;
}

export interface IngestionDetailItem {
  handle: string;
  status: string;
  id?: number;
  initial_pipeline_status?: string;
  already_contacted?: boolean;
}

export interface IngestionAuditReport {
  total_rows: number;
  imported: number;
  queued_for_ai_count: number;
  in_batch_duplicates_skipped: number;
  already_in_db_skipped: number;
  already_contacted_in_ledger: number;
  duplicate_handles: string[];
  collision_details: CollisionDetail[];
  details: IngestionDetailItem[];
}

export interface LiveXLookupResponse {
  handle: string;
  name: string;
  location: string;
  bio: string;
  recent_tweets: string[];
  raw_tweets_text: string;
  can_dm: boolean;
  segment: string;
  x_user_id?: string | null;
  source_mode: string;
  api_connected: boolean;
  already_contacted: boolean;
  existing_ledger_status?: string | null;
}

export interface SingleCandidatePayload {
  handle: string;
  name: string;
  location: string;
  bio: string;
  recent_tweets: string;
  can_dm: boolean;
  segment: string;
  x_user_id?: string | null;
}

