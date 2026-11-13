#!/usr/bin/env bash
# Shared configuration for Feature 08 Contract & Playwright E2E Quality Gate (ln-522-manual-tester)

export E2E_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export E2E_RESULTS_DIR="${E2E_REPO_ROOT}/tests/manual/results"
export E2E_BACKEND_PORT="${E2E_BACKEND_PORT:-8001}"
export E2E_FRONTEND_PORT="${E2E_FRONTEND_PORT:-3100}"
export E2E_BACKEND_URL="http://127.0.0.1:${E2E_BACKEND_PORT}"
export E2E_FRONTEND_URL="http://localhost:${E2E_FRONTEND_PORT}"
export E2E_DB_PATH="${E2E_REPO_ROOT}/outreach_e2e.db"
export E2E_PYTHON="${E2E_PYTHON:-python}"
export E2E_LOG_FILE="${E2E_RESULTS_DIR}/latest-run.log"
export E2E_SUMMARY_FILE="${E2E_RESULTS_DIR}/summary.md"

