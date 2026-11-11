# Current Active Feature: Project Setup & WBS Task Foundations
*(Sprint Status & Active Tracking)*

---

## 1. Active Feature Info
- **Active Task:** WBS Task 4 (Dual Queue Engine & AI Send Dispatcher) & Task 3 (FastAPI REST Routes)
- **Completed Foundation Tasks:**
  - ✅ **Task 1:** [`01-data-pack-and-ingestion.md`](file:///d:/AssignmentFDE/context/features/01-data-pack-and-ingestion.md) (CSV normalizer, in-batch dedup, seed loader)
  - ✅ **Task 2:** [`02-database-and-state-machine.md`](file:///d:/AssignmentFDE/context/features/02-database-and-state-machine.md) (SQLite schema, WAL mode, ORM models, unique idempotency constraints)
  - 🔄 **Task 3:** [`03-auth-and-security.md`](file:///d:/AssignmentFDE/context/features/03-auth-and-security.md) (Password hashing & JWT logic implemented; Auth REST routes pending)
- **Next Spec Reference:** [`04-dual-queue-and-ai-send-engine.md`](file:///d:/AssignmentFDE/context/features/04-dual-queue-and-ai-send-engine.md)
- **Current Status:** `IN_PROGRESS`

---

## 2. Completed Milestones
1. ✅ **Repository & Context Foundation:** Initialized structured context, specifications, and WBS execution plan.
2. ✅ **Database Models (`backend/app/models/`):**
   - `User`: Account management & partner roles.
   - `Candidate`: 9-state lifecycle with profile context & AI draft fields.
   - `OutreachLedger`: Strict 1-to-1 unique foreign key preventing duplicate dispatch.
   - `JobQueue`: Persistent asynchronous task queue for AI evaluation and DM sending.
3. ✅ **Ingestion Engine (`backend/app/services/ingestion.py`):**
   - Silent handle normalizer (lowercase, trim whitespace, strip `@`).
   - In-batch deduplication (merging duplicates like `P002` & `P020`).
   - Historical ledger cross-checking against previous outreach log.
4. ✅ **Bootstrap Seeding Script (`backend/seed_data.py`):**
   - Auto-creates default Partner user (`partner@genaifund.ai`).
   - Seeds 20 realistic candidate profiles from `candidates_seed.csv`.
   - Seeds 4 historical ledger records (`OUT-101` to `OUT-104`).
5. ✅ **Automated Pytest Suite (`backend/tests/test_ingestion.py`):**
   - 5/5 test cases PASSED (verifying idempotency, handle sanitization, duplicate protection).

---

## 3. Next Immediate Steps (Task 4 Execution)
1. **Implement AI Fit Scorer & Grounded DM Service (`backend/app/services/ai_scorer.py`):**
   - Google Gemini Flash / OpenAI client integration with structured Pydantic schema output.
   - Prompt Injection Defense (Fortified Delimiters `<untrusted_candidate_data>` against `P017`).
   - Sparse profile detection (`insufficient_evidence = true` for `P018`).
   - Evidence Grounding Guard (assert `evidence_snippet` is a valid substring of raw bio/tweets).
2. **Implement Safe Send Dispatcher Service (`backend/app/services/dispatcher.py`):**
   - Dual-Mode dispatch: Sandbox Simulator vs. Live X API.
   - Rate limiting via Token Bucket.
   - Closed DM protection (`can_dm = false` -> `SEND_BLOCKED`).
   - Safety whitelist enforcement (`ALLOWED_TEST_HANDLES`).
3. **Build FastAPI REST API Endpoints:**
   - `/api/auth` (Register, Login, Me, 1-Click Demo Login)
   - `/api/candidates` (List with filters, Ingest Seed, Ingest CSV, Ingest Single Handle)
   - `/api/outreach` (Approve & Send, Reject, Record Reply)
   - `/api/dashboard` (KPIs, Ledger list, Calibration benchmark)
