#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

mkdir -p "${E2E_RESULTS_DIR}"
rm -rf "${E2E_RESULTS_DIR}/traces"
mkdir -p "${E2E_RESULTS_DIR}/traces"
: > "${E2E_LOG_FILE}"

echo "=== Feature 08 Quality Gate: Tier 1 Contracts + Tier 2 Playwright E2E ===" | tee -a "${E2E_LOG_FILE}"
echo "Started at: $(date -Iseconds)" | tee -a "${E2E_LOG_FILE}"

cd "${E2E_REPO_ROOT}"

echo "" | tee -a "${E2E_LOG_FILE}"
echo "[Tier 1] Running Backend Contract Tests (pytest)..." | tee -a "${E2E_LOG_FILE}"
"${E2E_PYTHON}" -m pytest backend/tests/contracts/ -v --junitxml="${E2E_RESULTS_DIR}/contracts-junit.xml" 2>&1 | tee -a "${E2E_LOG_FILE}"

echo "" | tee -a "${E2E_LOG_FILE}"
echo "[Tier 2] Running Playwright E2E Suite (PW-01..PW-09)..." | tee -a "${E2E_LOG_FILE}"
cd "${E2E_REPO_ROOT}/frontend"
npx playwright test 2>&1 | tee -a "${E2E_LOG_FILE}"

echo "" | tee -a "${E2E_LOG_FILE}"
echo "[PASS] Quality Gate completed at $(date -Iseconds)" | tee -a "${E2E_LOG_FILE}"

cat > "${E2E_SUMMARY_FILE}" <<EOF
# Feature 08 Quality Gate Summary

- **Status:** PASS
- **Timestamp:** $(date -Iseconds)
- **Tier 1:** \`backend/tests/contracts/\` -> PASS (\`tests/manual/results/contracts-junit.xml\`)
- **Tier 2:** \`frontend/e2e/specs/pw-01..pw-09\` -> PASS (\`tests/manual/results/playwright-results.json\`, \`frontend/playwright-report/\`)
EOF

