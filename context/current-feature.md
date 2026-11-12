# Current Active Feature: Feature 01 – Data Pack & Scouting Ingestion (Full-Stack)
*(Sprint Status & Active Tracking)*

---

## 1. Active Feature Info
- **Active Task:** WBS Task 1 (Full-Stack Implementation): [`01-data-pack-and-ingestion.md`](file:///d:/AssignmentFDE/context/features/01-data-pack-and-ingestion.md)
  - ✅ **Sub-task 1.1 (Backend Ingestion Service Enhancement):** Upgraded [`backend/app/services/ingestion.py`](file:///d:/AssignmentFDE/backend/app/services/ingestion.py) with URL-aware `normalize_handle`, `ingest_seed_pack`, `preflight_csv_check`, `lookup_x_handle` (Live X API v2 + Seed/Synthetic Fallback), and enriched Audit Report (`collision_details`, `duplicate_handles`, `queued_for_ai_count`).
  - ✅ **Sub-task 1.2 (Backend FastAPI Ingestion Router & App Entrypoint):** Created [`backend/app/api/ingestion.py`](file:///d:/AssignmentFDE/backend/app/api/ingestion.py) (`POST /api/ingestion/seed`, `POST /api/ingestion/preflight`, `POST /api/ingestion/csv`, `GET /api/ingestion/x-lookup`, `POST /api/ingestion/single`, `GET /api/ingestion/template`) and [`backend/app/main.py`](file:///d:/AssignmentFDE/backend/app/main.py) with CORS and lifespan initialization.
  - ✅ **Sub-task 1.3 (Backend Automated Tests):** Expanded [`backend/tests/test_ingestion.py`](file:///d:/AssignmentFDE/backend/tests/test_ingestion.py) to 9 comprehensive unit & API integration tests covering URL normalization, pre-flight validation, 1-click seed pack audit metrics (16 queued, 1 in-batch dedup, 3 historical collisions), Live X lookup fallback, and FastAPI endpoints (`9/9 PASSED`).
  - ✅ **Sub-task 1.4 (Frontend Types, API Client & i18n Keys):** Created [`frontend/src/types/ingestion.ts`](file:///d:/AssignmentFDE/frontend/src/types/ingestion.ts), [`frontend/src/lib/ingestion-api.ts`](file:///d:/AssignmentFDE/frontend/src/lib/ingestion-api.ts) (with seamless client-side fallback), and symmetrical i18n keys in [`en.json`](file:///d:/AssignmentFDE/frontend/src/locales/en.json) and [`vi.json`](file:///d:/AssignmentFDE/frontend/src/locales/vi.json).
  - ✅ **Sub-task 1.5 (Frontend Triple-Tab Ingestion Hub UI):** Built [`SeedPackTab.tsx`](file:///d:/AssignmentFDE/frontend/src/components/ingestion/SeedPackTab.tsx) (Wireframe 1), [`CsvUploadTab.tsx`](file:///d:/AssignmentFDE/frontend/src/components/ingestion/CsvUploadTab.tsx) (Wireframe 2), [`LiveXLookupTab.tsx`](file:///d:/AssignmentFDE/frontend/src/components/ingestion/LiveXLookupTab.tsx) (Wireframe 3), [`IngestionAuditCard.tsx`](file:///d:/AssignmentFDE/frontend/src/components/ingestion/IngestionAuditCard.tsx), and [`frontend/src/app/ingestion/page.tsx`](file:///d:/AssignmentFDE/frontend/src/app/ingestion/page.tsx).
  - ✅ **Sub-task 1.6 (End-to-End Verification):** Verified `python -m pytest backend/tests/ -v` (`9 passed`) and `npm run build` in `frontend/` (`6/6 static pages generated, 0 errors`).
- **Completed Foundation Tasks:**
  - ✅ **Task 0:** [`00-base-layout-design-system.md`](file:///d:/AssignmentFDE/context/features/00-base-layout-design-system.md) (Atomic Design System, Pure Tailwind v4 `@theme`, English-First i18n, Paginated Table & AppShell)
  - ✅ **Task 1:** [`01-data-pack-and-ingestion.md`](file:///d:/AssignmentFDE/context/features/01-data-pack-and-ingestion.md) (Full-Stack Triple-Tab Ingestion Hub, Pre-flight CSV Check, Live X Lookup & 3-Tier Deduplication)
  - ✅ **Task 2:** [`02-database-and-state-machine.md`](file:///d:/AssignmentFDE/context/features/02-database-and-state-machine.md) (SQLite schema, WAL mode, ORM models, unique idempotency constraints)
- **Next Spec Reference:** [`03-auth-and-session.md`](file:///d:/AssignmentFDE/context/features/03-auth-and-session.md) & [`04-dual-queue-and-ai-send-engine.md`](file:///d:/AssignmentFDE/context/features/04-dual-queue-and-ai-send-engine.md)
- **Current Status:** `COMPLETED (Feature 01)`

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
