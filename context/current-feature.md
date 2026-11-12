# Current Active Feature: Frontend Base Layout, Navigation Shell & Atomic Design System
*(Sprint Status & Active Tracking)*

---

## 1. Active Feature Info
- **Active Task:** WBS Task 0 / Foundation: [`00-base-layout-design-system.md`](file:///d:/AssignmentFDE/context/features/00-base-layout-design-system.md)
  - Next.js 15 App Router + Tailwind CSS Theme Tokens
  - Exclusively `lucide-react` for all icons
  - Bilingual i18n Architecture (`en` & `vi`)
  - BreakpointLayout (Mobile, Tablet, Desktop)
  - Atoms & Molecules Catalog (`Button`, `Badge`, `ScorePill`, `Tabs`, `Compound Paginated Table`, `Modal`, `Drawer`, `StatCard`, `EvidenceMark`, `InlineComposer`, `ToastNotification`, `FileDropzone`)
  - AppShell with Collapsible Sidebar (`w-64` <-> `w-16`) & Top Header
  - Error Screens (401, 403, 500, Global Error Boundary)
- **Completed Foundation Tasks:**
  - ✅ **Task 0 (Spec):** [`00-base-layout-design-system.md`](file:///d:/AssignmentFDE/context/features/00-base-layout-design-system.md) (Atomic Design System, Tailwind v4 tokens, Paginated Table & Component Catalog)
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
