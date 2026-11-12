# Current Active Feature: Feature 02 – Database Schema, ORM Models & 9-State Lifecycle Machine
*(Sprint Status & Active Tracking)*

---

## 1. Active Feature Info
- **Active Task:** WBS Task 2 (State Machine, Idempotency Gate & Candidate API): [`02-database-and-state-machine.md`](file:///d:/AssignmentFDE/context/features/02-database-and-state-machine.md)
  - ✅ **Sub-task 2.1 (SQLite WAL Mode & ORM Schema Constraints):** Configured [`backend/app/core/database.py`](file:///d:/AssignmentFDE/backend/app/core/database.py) (`PRAGMA journal_mode=WAL`, `PRAGMA foreign_keys=ON`) and 4 ORM models (`User`, `Candidate`, `OutreachLedger` with `UNIQUE(candidate_id)`, `UNIQUE(handle)`, `UNIQUE(idempotency_key)`, and `JobQueue`).
  - ✅ **Sub-task 2.2 (9-State Lifecycle Machine & Two-Tier Idempotency Gate):** Created [`backend/app/services/state_machine.py`](file:///d:/AssignmentFDE/backend/app/services/state_machine.py) enforcing legal transitions across all 9 states (`QUEUED_FOR_AI`, `PENDING_REVIEW`, `INSUFFICIENT_EVIDENCE`, `AI_FAILED`, `REJECTED`, `APPROVED_QUEUED`, `SEND_BLOCKED`, `SENT`, `REPLIED`) and the Two-Tier Zero Double-Messaging Gate (Application logic check + Database `IntegrityError` atomic catch returning `409 Conflict`).
  - ✅ **Sub-task 2.3 (Candidate Lifecycle & Outreach Action API Router):** Created [`backend/app/api/candidates.py`](file:///d:/AssignmentFDE/backend/app/api/candidates.py) (`GET /api/candidates`, `GET /api/candidates/state-summary`, `GET /api/candidates/{id}`, `POST /api/candidates/{id}/send`, `POST /api/candidates/{id}/reject`, `POST /api/candidates/{id}/retry`, `POST /api/candidates/{id}/reply`, `POST /api/candidates/{id}/handled`) and registered in [`backend/app/main.py`](file:///d:/AssignmentFDE/backend/app/main.py).
  - ✅ **Sub-task 2.4 (Automated Pytest Suite for State Machine & Idempotency):** Created [`backend/tests/test_state_machine.py`](file:///d:/AssignmentFDE/backend/tests/test_state_machine.py) verifying all Acceptance Criteria in `02-database-and-state-machine.md` (Double-click `409 Conflict` idempotency test, Seed History `already_contacted` protection test, Closed DM `SEND_BLOCKED` test, 9-state transition rules, and SQLite WAL persistence).
  - ✅ **Sub-task 2.5 (End-to-End Verification & Sprint Log Update):** Verified `python -m pytest backend/tests/ -v` -> **14/14 PASSED** (`9` in `test_ingestion.py` + `5` in `test_state_machine.py`).
- **Completed Foundation Tasks:**
  - ✅ **Task 0:** [`00-base-layout-design-system.md`](file:///d:/AssignmentFDE/context/features/00-base-layout-design-system.md) (Atomic Design System, Pure Tailwind v4 `@theme`, English-First i18n, Paginated Table & AppShell)
  - ✅ **Task 1:** [`01-data-pack-and-ingestion.md`](file:///d:/AssignmentFDE/context/features/01-data-pack-and-ingestion.md) (Full-Stack Triple-Tab Ingestion Hub, Pre-flight CSV Check, Live X Lookup & 3-Tier Deduplication)
  - ✅ **Task 2:** [`02-database-and-state-machine.md`](file:///d:/AssignmentFDE/context/features/02-database-and-state-machine.md) (SQLite WAL Schema, 9-State Lifecycle Machine, Two-Tier Zero Double-Messaging Gate & Candidate Lifecycle API)
- **Next Spec Reference:** [`03-auth-and-session.md`](file:///d:/AssignmentFDE/context/features/03-auth-and-session.md) & [`04-dual-queue-and-ai-send-engine.md`](file:///d:/AssignmentFDE/context/features/04-dual-queue-and-ai-send-engine.md)
- **Current Status:** `COMPLETED (Feature 02)`

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
6. ✅ **Frontend Design System Implementation (`frontend/`):**
   - Initialized Next.js 15 App Router project structure with TypeScript and Tailwind CSS.
   - Design tokens configured in CSS (`--color-primary`, `--color-destructive`, etc.) matching Venture Capital theme.
   - Built full Atomic Design System:
     - **Atoms:** `Button`, `Badge` (with `urgent` pulse), `ScorePill` (0..4), `Input`, `Textarea` (with live counter), `EvidenceMark` (amber `<mark>`).
     - **Molecules:** `Tabs` (`LineTabs`, `PillTabs`), `TablePagination` (10/25/50 selector), `StatCard`, `InlineComposer`, `EvidenceCallout`, `FileDropzone`, `ToastNotification`.
     - **Organisms:** `AppSidebar` (collapsible w-64 vs w-16), `TopHeader`, `DataTable` compound, `Modal`, `Drawer`, `ErrorViews` (401, 403, 500), `GlobalErrorBoundary`.
     - **Layout:** `AppProviders`, `BreakpointLayout`, `AppShell`.
     - **i18n:** Bilingual English/Vietnamese dictionary with instant in-memory toggle.
   - Verified via `npm run build` -> **Compiled successfully (5/5 static pages) with 0 errors**.
7. ✅ **Strict i18n Architecture & English-First Rules:**
   - Established English (`en`) as the primary/default language across all components (standard for international VC & evaluation).
   - Removed 100% of hardcoded Vietnamese and mixed bilingual strings from templates; all user-facing copy is now routed through `useI18n().t()`.
   - Created symmetrical translation dictionaries in `locales/en.json` and `locales/vi.json`.
   - Updated Rule in [`00-base-layout-design-system.md`](file:///d:/AssignmentFDE/context/features/00-base-layout-design-system.md#L200-L225).
8. ✅ **Strict Coding Standards & Pure Tailwind CSS v4 Adoption:**
   - Documented full coding standards in [`context/coding-standards.md`](file:///d:/AssignmentFDE/context/coding-standards.md).
   - Upgraded `frontend/` to pure **Tailwind CSS v4** (`@tailwindcss/postcss: ^4.3.5`, `tailwindcss: ^4.3.5`).
   - Completely removed legacy `tailwind.config.ts`; all theme variables and styling rules are 100% CSS-driven via `@theme` in `src/app/globals.css`.
   - Verified via `npm run build` -> **Compiled successfully (5/5 static pages) with 0 errors**.
9. ✅ **Full-Stack Implementation of Feature 01 (`01-data-pack-and-ingestion.md`):**
   - **Backend Ingestion Service (`backend/app/services/ingestion.py`):**
     - Upgraded `normalize_handle` to strip `@`, quotes, whitespace, and extract usernames from full `https://x.com/...` or `https://twitter.com/...` URLs.
     - Implemented `preflight_csv_check` for non-destructive CSV validation and 5-row preview generation.
     - Implemented `ingest_seed_pack` (1-Click 20 SEA profile loader with 3-tier deduplication: 16 queued for AI, 1 in-batch duplicate `@minh_quant` merged, 3 past sent/replied ledger collisions `@linhtran_robo`, `@putri_agentic`, `@harith_medai` protected).
     - Implemented `lookup_x_handle` supporting Live X API v2 (`X_BEARER_TOKEN`) with automatic fallback to SQLite/Seed Pack/Synthetic preview.
   - **FastAPI Endpoints (`backend/app/api/ingestion.py` & `backend/app/main.py`):**
     - `POST /api/ingestion/seed`, `POST /api/ingestion/preflight`, `POST /api/ingestion/csv`, `GET /api/ingestion/x-lookup`, `POST /api/ingestion/single`, and `GET /api/ingestion/template`.
   - **Automated Pytest Suite (`backend/tests/test_ingestion.py`):**
     - Expanded to 9 unit & FastAPI integration tests -> **9/9 PASSED**.
   - **Frontend Triple-Tab Ingestion Hub (`frontend/src/app/ingestion/page.tsx` & `frontend/src/components/ingestion/`):**
     - Built `SeedPackTab.tsx` (Wireframe 1), `CsvUploadTab.tsx` (Wireframe 2), `LiveXLookupTab.tsx` (Wireframe 3), and `IngestionAuditCard.tsx`.
     - **UX Refinement:** Chuyển `IngestionAuditCard` thành Primary View nổi bật ngay vị trí chính khi thực hiện nạp dữ liệu xong (thay vì chèn xuống cuối), tích hợp nút `[↺ Quay lại Biểu mẫu / Nạp tiếp]` và `[🚀 Chuyển tới Bàn duyệt HITL]`.
     - Added full symmetrical English/Vietnamese i18n dictionary under `ingestion.*` in `en.json` and `vi.json`.
     - Verified via `npm run build` -> **Compiled successfully (6/6 static pages including `/ingestion`) with 0 errors**.
10. ✅ **Full Implementation of Feature 02 (`02-database-and-state-machine.md`):**
    - **9-State Lifecycle Machine (`backend/app/services/state_machine.py`):**
      - Implemented formal `ALLOWED_TRANSITIONS` matrix across all 9 states (`QUEUED_FOR_AI`, `PENDING_REVIEW`, `INSUFFICIENT_EVIDENCE`, `AI_FAILED`, `REJECTED`, `APPROVED_QUEUED`, `SEND_BLOCKED`, `SENT`, `REPLIED`).
      - Prevented terminal outreach states (`SENT`, `REPLIED`) from ever regressing to pre-send states.
    - **Two-Tier Idempotency & Zero Double-Messaging Gate (`approve_and_send_candidate`):**
      - *Tier 1 (Application Guard):* Verifies candidate status, existing `outreach_ledger` entries (`candidate_id` or `handle`), and `idempotency_key` before dispatch -> returns `409 Conflict` on duplicate attempts.
      - *Closed DM Guard:* Automatically transitions `can_dm = False` profiles (`@arjun_infer`) to `SEND_BLOCKED` (`422 Unprocessable Entity`) and records a `BLOCKED` ledger entry.
      - *Tier 2 (Database Unique Constraint + Atomic Transaction):* Catches `sqlalchemy.exc.IntegrityError` on concurrent double-clicks and rolls back cleanly with `409 Conflict`.
    - **Candidate Lifecycle REST API (`backend/app/api/candidates.py`):**
      - Implemented `GET /api/candidates`, `GET /api/candidates/state-summary`, `GET /api/candidates/{id}`, `POST /api/candidates/{id}/send`, `POST /api/candidates/{id}/reject`, `POST /api/candidates/{id}/retry`, `POST /api/candidates/{id}/reply`, and `POST /api/candidates/{id}/handled`.
    - **Automated Pytest Suite (`backend/tests/test_state_machine.py`):**
      - Added 5 comprehensive tests covering double-click idempotency (`409 Conflict`), seed history protection (`@linhtran_robo`), closed DM protection (`@arjun_infer`), 9-state lifecycle transitions + reply/handled workflow, and file-backed SQLite WAL persistence across server restarts -> **14/14 total tests PASSED**.

---

## 3. Next Immediate Steps (Task 4 & Task 3 Backend Execution)
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
