# GenAI Fund – Autonomous Scouting & Personalized Outreach System

Hướng dẫn từng bước (**Step-by-Step Guide**) để cài đặt môi trường, dán các API Key thật (Gemini/OpenAI & X API v2), reset dữ liệu sạch chỉ giữ User, chạy kiểm chứng tự động và thực hiện **Manual QA** trên giao diện.

> Tài liệu kiến trúc & lộ trình triển khai Docker / AWS tiếp theo: [`context/features/07-verification-and-handover.md`](context/features/07-verification-and-handover.md)

---

## 1. Hướng đi Tổng thể (Workflow Approach)

Hệ thống được thiết kế theo kiến trúc **2 tầng tách biệt + Chế độ Kép (Sandbox $0 ↔ Live API)**:
1. **Backend (`FastAPI` + `SQLite WAL` + Dual Queue):** Chạy tại `http://127.0.0.1:8000`, đảm nhiệm Ingestion khử trùng lặp 3 tầng, chấm điểm AI Tri-Guard chống Prompt Injection/Sparse, máy trạng thái 9 bước, và chốt chặn chống gửi trùng lặp `OutreachLedger`.
2. **Frontend (`Next.js 15 App Router` + BFF Cookie):** Chạy tại `http://localhost:3000`, quản lý phiên đăng nhập `HttpOnly` cookie qua `/api/auth/login`, song ngữ `EN / VI` và giao diện HITL Candidate Review.
3. **Chiến lược Kiểm chứng trước khi đóng gói Docker/AWS:**
   - **Bước A:** Giữ bộ test tự động chạy offline (`$0`, không cần key).
   - **Bước B (Giai đoạn hiện tại):** Dán API key thật vào `backend/.env` $\rightarrow$ chạy diagnostic script `verify_live_keys.py` $\rightarrow$ chạy `reset_clean_users.py` để làm sạch DB $\rightarrow$ mở web check tay theo [`tests/manual/MANUAL_QA_CHECKLIST.md`](tests/manual/MANUAL_QA_CHECKLIST.md).
   - **Bước C (Kế tiếp):** Đóng gói Docker Compose (Sub-task 7.3) & Deploy AWS Terraform `dev`/`staging`/`prod` (Sub-task 7.5).

---

## 2. Cài đặt Dependencies (Chạy 1 lần đầu)

Mở PowerShell tại thư mục gốc `d:\AssignmentFDE`:

```powershell
# 1. Cài dependencies Backend (Python 3.10+)
pip install -r backend/requirements.txt

# 2. Cài dependencies Frontend (Node.js 20+)
cd frontend
npm.cmd install
cd ..
```

---

## 3. Cấu hình API Keys để Test Thật (`backend/.env`)

Nếu chưa có file `backend/.env`, copy từ file mẫu [`backend/.env.example`](backend/.env.example):

```powershell
Copy-Item backend/.env.example backend/.env
```

Mở `backend/.env` và dán các key tương ứng với phần bạn muốn kiểm thử thật:

| Nhóm Kiểm thử | Biến môi trường cần dán trong `backend/.env` | Lưu ý & Hành vi thực tế |
| :--- | :--- | :--- |
| **1. Live AI Chấm điểm & Soạn DM** *(chọn 1 trong 2)* | `GEMINI_API_KEY=<key_cua_ban>`<br>*(hoặc)* `OPENAI_API_KEY=<key_cua_ban>` | - Nếu điền cả 2, backend ưu tiên `GEMINI_API_KEY` (`gemini-3.5-flash` + fallback list).<br>- Nếu để trống cả 2, hệ thống tự chạy bằng bộ chấm điểm deterministic `$0`. |
| **2. Live X Lookup & Local Simulator ($0)** *(Tab `X Lookup` trên UI)* | - **Dùng X thật:** `X_API_BASE_URL=https://api.twitter.com/2` + `X_BEARER_TOKEN=<bearer_thật>`<br>- **Dùng Simulator `$0` ở Dev:** `X_API_BASE_URL=http://127.0.0.1:8099/2` **VÀ** `X_BEARER_TOKEN=sim_dev_bearer_token` | - Hệ thống **KHÔNG còn silent fallback**: thiếu key trả `HTTP 503`; X trả `401`/`402`/`403`/`404`/`429` (VD: hết credit `$0` báo `402 credits depleted`) sẽ hiện nguyên mã lỗi thật lên UI & API.<br>- **Quan trọng:** Khi dùng Simulator phải có **cả `X_API_BASE_URL` lẫn `X_BEARER_TOKEN`** trong `backend/.env` (thiếu `X_API_BASE_URL` sẽ gửi token giả lên X thật và dính `401`).<br>- **Bắt buộc restart `uvicorn`** sau khi sửa `backend/.env` (`uvicorn --reload` chỉ watch file `.py`, không tự nạp lại `.env`). |
| **3. Live X DM Dispatch** *(Tùy chọn gửi DM thật)* | `DISPATCH_MODE=LIVE_X`<br>`LIVE_X_DRY_RUN=False`<br>`ALLOWED_TEST_HANDLES=<handle_test_cua_ban>`<br>`X_API_KEY=...`<br>`X_API_SECRET=...`<br>`X_ACCESS_TOKEN=...`<br>`X_ACCESS_TOKEN_SECRET=...` | - **An toàn tuyệt đối:** Backend **chỉ gửi DM thật** nếu handle nằm đúng trong `ALLOWED_TEST_HANDLES`. Mọi handle ngoài danh sách đều bị chặn (`422 SEND_BLOCKED`).<br>- App trên X Developer Portal cần quyền **Read and write and Direct message**.<br>- Nếu chỉ muốn test UI mà **không** gửi DM thật ra ngoài, giữ nguyên `DISPATCH_MODE=SANDBOX`. |

*(Các biến cơ bản giữ nguyên mặc định: `PORT=8000`, `DATABASE_URL=sqlite:///./outreach.db`, `SECRET_KEY=...`)*

---

## 4. Các Script Điều khiển Dữ liệu & Kiểm chứng Key (CLI)

Chạy tại thư mục gốc `d:\AssignmentFDE`:

### A. Reset Dữ liệu Sạch Chỉ Giữ User Đăng nhập *(Khuyên dùng trước Manual Check)*
Xóa sạch toàn bộ `candidates`, `outreach_ledger`, `job_queue`, **chỉ giữ lại tài khoản đăng nhập**:

```powershell
# Chỉ giữ Partner (partner@genaifund.ai / GenAIFund2026!)
python -m backend.reset_clean_users --yes

# Giữ Partner + tạo thêm Analyst (analyst@genaifund.ai / Analyst2026!) để test phân quyền /403
python -m backend.reset_clean_users --yes --with-analyst
```

*(Hoặc nếu muốn nạp sẵn 20 profiles mẫu + 4 lịch sử ledger ngay lập tức: chạy `python backend/seed_data.py`)*

### B. Kiểm chứng Live AI & Live X Key trước khi mở Web
```powershell
# 1. Kiểm tra tổng thể tất cả key đã nhận diện đúng chưa (Gate L1 + L2 + L3)
python -m backend.scripts.verify_live_keys --mode all

# 2. Chạy chấm điểm THẬT bằng Gemini/OpenAI trên toàn bộ 19 hồ sơ unique & đo Alignment % + Latency
python -m backend.scripts.verify_live_keys --mode llm --full-benchmark --json-out tests/manual/results/live-verify-report.json

# 3. Kiểm tra tra cứu X API v2 thật với một handle bất kỳ
python -m backend.scripts.verify_live_keys --mode x --handle OpenAI

# 4. Kiểm tra chốt chặn whitelist LIVE_X (Dry-run an toàn, không bắn DM thật)
python -m backend.scripts.verify_live_keys --mode dispatch

# 5. (CHỈ DÙNG KHI MUỐN BẮN 1 DM TEST THẬT) Gửi thử tới handle đã có trong ALLOWED_TEST_HANDLES
python -m backend.scripts.verify_live_keys --mode dispatch --execute-send --dm-handle <handle_trong_whitelist>
```

---

## 5. Khởi chạy Web App để Manual Check

Mở **2 cửa sổ PowerShell** tại `d:\AssignmentFDE` *(hoặc 3 cửa sổ nếu dùng Local X Simulator `$0`)*:

**Terminal 0 *(Tùy chọn $0 Dev)* — Local X API v2 Simulator (`:8099`):**

File [`backend/scripts/x_simulator.py`](backend/scripts/x_simulator.py) đã tự gọi Uvicorn bên trong nên **không gõ thêm `uvicorn`** ở Cách 1 (nếu gọi qua `uvicorn` phải chỉ rõ `:simulator_app`):

```powershell
# Cách 1 (khuyên dùng, bỏ uvicorn):
python -m backend.scripts.x_simulator --host 127.0.0.1 --port 8099

# Cách 2 (nếu gọi qua uvicorn):
python -m uvicorn backend.scripts.x_simulator:simulator_app --host 127.0.0.1 --port 8099
```

- Kiểm tra nhanh Simulator đang sống tại: `http://127.0.0.1:8099/health` (`{"status":"ok", ...}`).
- Giữ cửa sổ này chạy song song khi test tab **X Lookup** ở `$0`. Thử nhập `@sim_401`, `@credits_depleted`, `@forbidden_handle`, `@missing_user`, `@rate_limit` để kiểm chứng UI hiển thị đúng từng mã lỗi `401` / `402` / `403` / `404` / `429`.

**Terminal 1 — Backend FastAPI (`:8000`):**
```powershell
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Frontend Next.js (`:3000`):**
```powershell
cd frontend
npm.cmd run dev
```

Sau đó mở trình duyệt tại **`http://localhost:3000/login`** và đăng nhập với tài khoản điền sẵn:
- **Partner (Full quyền):** `partner@genaifund.ai` / `GenAIFund2026!`
- **Analyst (Nếu reset bằng `--with-analyst`, để test chặn `/calibration` $\rightarrow$ `/403`):** `analyst@genaifund.ai` / `Analyst2026!`

---

## 6. Thứ tự Manual Check Nhanh trên Giao diện

Checklist chi tiết lưu tại [`tests/manual/MANUAL_QA_CHECKLIST.md`](tests/manual/MANUAL_QA_CHECKLIST.md). Luồng đi nhanh đề xuất sau khi đã `reset_clean_users --yes`:

1. **Login & Workspace trắng (`/login` $\rightarrow$ `/`):**
   - Kiểm tra form Login gọn (`Sign In`, đã bỏ badge prefill & footer XSS).
   - Vào `/` thấy khối 4 thẻ KPI mặc định **đang thu gọn**, nút `Show Metrics` / `Hide Metrics` nằm ngay cạnh `Process Queue` & `Refresh` trên thanh công cụ $\rightarrow$ bấm để kiểm tra đóng/mở KPI. Badge sidebar cạnh **Candidate Review** phản ánh đúng số `PENDING_REVIEW` trong SQLite.
2. **Nạp dữ liệu 3 cách (`/ingestion`):**
   - **Tab `X Lookup`:** Nhập 1 handle (vd `@minh_quant`, `@arjun_infer` hoặc `@OpenAI`) $\rightarrow$ xác nhận badge `Local X API v2 Simulator ($0 HTTP)` (hoặc `Live Mode`), bio & tweets load qua HTTP $\rightarrow$ bấm đẩy vào AI Queue.
   - **Tab `Starter Pack`:** Bấm `Load Starter Pack` $\rightarrow$ kiểm tra Audit Report (20 rows, gộp duplicate `P002`/`P020`).
   - **Tab `CSV Import`:** Giao diện ban đầu chỉ hiện Dropzone; ngay khi chọn/tải file `.csv`, hệ thống mới hiển thị **CSV Required Columns Status** (trạng thái `Found` / `Missing` cho từng cột `handle`, `name`, `bio`, `recent_tweets` + các header đọc được) và bảng **PRE-FLIGHT DATA PREVIEW (FIRST 5 ROWS)**. Thử `missing_bio.csv` (báo đỏ thiếu cột `bio`, khóa nút Import) và file chuẩn.
3. **Chấm AI thật & Duyệt DM (`/`):**
   - Bấm `Process Queue` để Live Gemini/OpenAI chấm hàng loạt.
   - Kiểm tra cột điểm `4 / 4`, `3 / 4`, `1 / 4` hiển thị **đúng 1 dòng**.
   - Bấm `Review` trên 1 hồ sơ `4 / 4`: kiểm tra đoạn highlight màu vàng khớp nguyên văn bio/tweet; bấm `Regenerate with AI` để thử gọi Live LLM tạo nháp mới; thanh nút **Reject · Cancel · Approve & Send DM** nằm cố định ở footer đáy modal.
   - Kiểm tra `P017` (Prompt Injection $\rightarrow$ `1 / 4`, DM rỗng), `P018` (Sparse $\rightarrow$ `0 / 4`, `INSUFFICIENT_EVIDENCE`), `P019` (`@arjun_infer` khóa nút gửi).
   - Bấm `Approve & Send DM` cho `@minh_quant` (chế độ `SANDBOX`, hoặc `LIVE_X` nếu đã đưa handle test vào whitelist) $\rightarrow$ mở lại kiểm tra cảnh báo khóa chống gửi đúp (`409`).
4. **Outreach Log, Reply & Calibration (`/ledger`, `/calibration`):**
   - Vào `/ledger`: trang chỉ gọi `/api/ledger` (không kéo theo `/calibration`), kiểm tra header bảng 1 từ (`ID`, `Candidate`, `Message`, `Channel`, `Reply`, `Actions`), bấm `Log Reply` $\rightarrow$ hiện badge `URGENT`, mở `Audit Trail`, bấm `Mark Handled`.
   - Chuyển sang tab/trang `/calibration`: `/api/ledger/calibration` dùng điểm có sẵn trong SQLite hoặc Tri-Guard local (`0` token, phản hồi tức thì, không gọi lại Gemini cho các hồ sơ chưa nạp).
   - Chuyển đổi ngôn ngữ `EN` $\leftrightarrow$ `VI` trên menu góc phải trên.

---

## 7. Bộ Kiểm thử Tự động (Chạy lại bất kỳ lúc nào)

Các bộ test này chạy hoàn toàn cô lập (dùng `sqlite:///:memory:` và `outreach_e2e.db` ở cổng `3100`/`8001`/`8099`), **không ghi đè** dữ liệu test tay của bạn trên `outreach.db` và **không tốn tiền API**:

```powershell
# Kiểm tra TypeScript Frontend (an toàn, không đè thư mục .next của next dev)
cd frontend; npx.cmd tsc --noEmit; cd ..

# Toàn bộ bộ test Backend (Unit + API Integration + Contracts + Reset/X-Client/Simulator Tools)
python -m pytest backend/tests/ -v

# Full Quality Gate 3 tầng (Tier 1: 6 Contract Tests + Tier 2: 9 Playwright E2E + Tier 3: E/R Result Contract)
# Lưu ý: tắt trước terminal x_simulator (:8099) nếu đang mở tay vì Playwright tự khởi động server riêng trên cổng 8099
powershell -ExecutionPolicy Bypass -File tests/manual/test-all.ps1

# Chạy riêng bước trung gian đối chiếu E/R Result Contract từ raw traces (ER-data-packing + ER-F5-F6 + 9 States)
python -m backend.scripts.build_er_result_contract
# (Chỉ dùng khi chủ đích cập nhật lại Golden Expected sau khi đổi thiết kế E/R):
# python -m backend.scripts.build_er_result_contract --update-expected
```

**Cơ chế Kiểm chứng E/R Result Contract (`ln-522-manual-tester` Expected-Based Testing):**
- Raw telemetry (`tests/manual/results/traces/raw/all-traces.jsonl` & `*.state.json`) ghi lại từng HTTP request và DB snapshot theo thứ tự thời gian.
- Script [`backend/scripts/build_er_result_contract.py`](backend/scripts/build_er_result_contract.py) đóng vai trò **bước trung gian** chiếu toàn bộ trace thô sang chuẩn **Result Contract** ([`tests/manual/results/traces/er_result_contract.json`](tests/manual/results/traces/er_result_contract.json)) rồi `diff` nghiêm ngặt (Fail-Fast) với Golden **Expected Contract** ([`backend/tests/contracts/expected/er_expected_contract.json`](backend/tests/contracts/expected/er_expected_contract.json)), đồng thời xuất báo cáo đối chiếu [`tests/manual/results/traces/_ER_CONTRACT_VERIFICATION.md`](tests/manual/results/traces/_ER_CONTRACT_VERIFICATION.md).
- Phạm vi phủ đối chiếu:
  - [`testing/ER-data-packing.md`](testing/ER-data-packing.md): Seed 20 dòng (`queued=16, dup=1, ledger_collisions=3`), thuộc tính phức hợp/đa trị (`location`, `recent_tweets` nối `||`), và kịch bản Cross-Batch `T1 -> T2 -> T3` (`IMPORTED`, `ALREADY_EXISTS_IN_DB`, `SKIPPED_IN_BATCH_DUPLICATE`, `HISTORICAL_COLLISION`, `jobs_total=1`, giữ nguyên `REPLIED`).
  - [`testing/ER-F5-F6.md`](testing/ER-F5-F6.md): Trọn bộ `T1 -> T2 -> T3 -> T4` gồm Reject `P009/P017`, khóa `422` `P019`, `AI_ASSESSMENT_DRAFT` (`evidence_snippet` verbatim, tách `draft_dm`/`edited_dm`, `OPTIMAL` 250–600 ký tự), tạo `OUT-105` & KPI Mốc T2–T3 (`dispatched=4`, `reply_rate=50% -> 75%`, `needs_attention=2 -> 3 -> 2`), khóa gửi trùng `409`, chặn reply `422` trên `OUT-104`, và `Partner Calibration Matrix` (`100.0%` alignment `19/19`, `2/2` safety blocks).
  - [`testing/e2e.md`](testing/e2e.md): Độ phủ 9/9 trạng thái State Machine (`8` trực tiếp trên DB/API + `APPROVED_QUEUED` trung gian đồng bộ).

---

## 8. Ghi chú Xử lý Lỗi Thường gặp (Troubleshooting)

| Triệu chứng / Thông báo lỗi | Nguyên nhân | Cách khắc phục |
| :--- | :--- | :--- |
| `ERROR: Error loading ASGI app. Import string "backend.scripts.x_simulator" must be in format "<module>:<attribute>"` | Gõ dư `uvicorn` khi chạy `x_simulator.py` | Bỏ chữ `uvicorn` (`python -m backend.scripts.x_simulator --host 127.0.0.1 --port 8099`) **hoặc** dùng `backend.scripts.x_simulator:simulator_app`. |
| `HTTP 401 [X API 401 Unauthorized]` dù đang dùng `sim_dev_bearer_token` | Thiếu `X_API_BASE_URL=http://127.0.0.1:8099/2` trong `backend/.env` hoặc quên restart `uvicorn` sau khi sửa `.env` | Thêm `X_API_BASE_URL=http://127.0.0.1:8099/2` vào `backend/.env` rồi `Ctrl+C` khởi động lại `uvicorn`. |
| `HTTP 503 Unable to reach X API endpoint (http://127.0.0.1:8099/2): [WinError 10061]` | Chưa bật Local X Simulator ở cổng `8099` | Chạy `python -m backend.scripts.x_simulator --host 127.0.0.1 --port 8099` ở một cửa sổ PowerShell riêng. |
| `HTTP 402 [X API 402 Payment Required] credits depleted` | Token X thật chưa nạp credit trả phí trên `console.x.com` | Nạp credit Pay-Per-Use nếu muốn test X thật, hoặc chuyển `X_API_BASE_URL=http://127.0.0.1:8099/2` dùng Simulator `$0`. |
| `ENOENT ... app-build-manifest.json` trong terminal Frontend `next dev` | Chạy `npm run build` (`next build`) trong lúc `next dev` đang mở làm ghi đè thư mục `.next` | Ở terminal Frontend bấm `Ctrl+C`, chạy `Remove-Item -Recurse -Force .next` rồi chạy lại `npm.cmd run dev`. |
| `GET /.well-known/appspecific/com.chrome.devtools.json 404` | Chrome/Edge DevTools (khi mở F12) tự dò cấu hình workspace cục bộ | Log vô hại của trình duyệt, hoàn toàn bình thường và không ảnh hưởng tới app. |
| Gọi `curl` trên PowerShell báo lỗi hoặc trả `401` | PowerShell alias `curl` trỏ tới `Invoke-WebRequest` (không hiểu `\` xuống dòng kiểu bash) hoặc thiếu `-b "session_token=..."` | Dùng `curl.exe` trên 1 dòng kèm cookie `-b "session_token=..."` (hoặc test trực tiếp trên UI). |

