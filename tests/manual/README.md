# Quality Gate: 2-Tier Contract + Playwright E2E Suite (Feature 08)

Suite kiểm thử tự động 2 tầng được tổ chức theo quy chuẩn `ln-522-manual-tester` (Fail-Fast + Expected-Based + Isolated E2E Environment).

## Cấu trúc Thư mục

- `config.sh`: Biến cấu hình dùng chung (`E2E_BACKEND_PORT=8001`, `E2E_FRONTEND_PORT=3100`, `outreach_e2e.db`, `results/`).
- `test-all.sh`: Quality Gate runner cho Linux/macOS/Git Bash (Fail-Fast).
- `test-all.ps1`: Quality Gate runner cho Windows PowerShell (Fail-Fast).
- `results/`: Thư mục chứa artifacts sau mỗi lần chạy (gitignored):
  - `contracts-junit.xml`: Kết quả Tier 1 Contract Tests.
  - `contract-diff-*.txt`: Diff chi tiết khi Tier 1 Contract mismatch với golden files.
  - `playwright-results.json` & `playwright-junit.xml`: Kết quả Tier 2 Playwright E2E.
  - `traces/_FLOW_COVERAGE_REPORT.md`: Báo cáo tổng hợp độ phủ **9/9 Trạng thái State Machine** và bảng ánh xạ từng testcase (`CT-*`, `PW-01`..`PW-09`) theo thiết kế `testing/e2e.md` & `testing/ER-*.md`.
  - `traces/<TESTCASE_ID>.md`: Trace Contract theo Flow từng Step nghiệp vụ (`STEP 1 -> STEP N`), DB Checkpoint Delta và các Guard kích hoạt (`401`/`409`/`422`).
  - `traces/raw/all-traces.jsonl`: Telemetry HTTP JSONL thô để đối chiếu chi tiết khi cần.
  - `summary.md` & `latest-run.log`: Báo cáo tổng hợp và log thực thi gần nhất.
- `frontend/playwright-report/`: HTML report trực quan của Playwright (mở bằng `cd frontend && npx.cmd playwright show-report`).

## Cách chạy

### Windows PowerShell (Recommended)
```powershell
powershell -ExecutionPolicy Bypass -File tests/manual/test-all.ps1
```

### Bash / Git Bash
```bash
bash tests/manual/test-all.sh
```

## Môi trường Cô lập (Isolated Test Environment)
- **Dev database (`outreach.db`) không bao giờ bị ghi đè.**
- Backend E2E chạy trên `127.0.0.1:8001` trỏ tới `outreach_e2e.db` (được reset deterministic qua `backend/tests/e2e_seed.py`).
- Frontend E2E chạy trên `localhost:3100` với thư mục build tách biệt `.next-e2e`.

