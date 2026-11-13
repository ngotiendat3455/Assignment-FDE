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
| **1. Live AI Chấm điểm & Soạn DM** *(chọn 1 trong 2)* | `GEMINI_API_KEY=<key_cua_ban>`<br>*(hoặc)* `OPENAI_API_KEY=<key_cua_ban>` | - Nếu điền cả 2, backend ưu tiên `GEMINI_API_KEY` (`gemini-2.0-flash`).<br>- Nếu để trống cả 2, hệ thống tự chạy bằng bộ chấm điểm deterministic `$0`. |
| **2. Live X Lookup** *(Tab `X Lookup` trên UI)* | `X_BEARER_TOKEN=<bearer_token_cua_ban>` | - Dùng cho `GET /api/ingestion/x-lookup` lấy bio & 5 tweet gần nhất thật từ X API v2.<br>- Nếu trống hoặc lỗi quota, tự fallback về Seed/Sandbox. |
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

Mở **2 cửa sổ PowerShell** tại `d:\AssignmentFDE`:

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
   - Vào `/` thấy khối 4 thẻ KPI mặc định **đang thu gọn** $\rightarrow$ bấm `Show Metrics` / `Hide Metrics` để kiểm tra. Bảng ứng viên đang trống (`0`).
2. **Nạp dữ liệu 3 cách (`/ingestion`):**
   - **Tab `X Lookup`:** Nhập 1 handle X thật (vd `@OpenAI` hoặc founder bất kỳ) $\rightarrow$ xác nhận hiện badge `"X API v2 Connected (Live Mode)"`, bio & tweets load từ X thật $\rightarrow$ bấm đẩy vào AI Queue.
   - **Tab `Starter Pack`:** Bấm `Load Starter Pack` $\rightarrow$ kiểm tra Audit Report (20 rows, gộp duplicate `P002`/`P020`).
   - **Tab `CSV Import`:** Thử file thiếu cột (bị chặn) và file chuẩn.
3. **Chấm AI thật & Duyệt DM (`/`):**
   - Bấm `Process Queue` để Live Gemini/OpenAI chấm hàng loạt.
   - Kiểm tra cột điểm `4 / 4`, `3 / 4`, `1 / 4` hiển thị **đúng 1 dòng**.
   - Bấm `Review` trên 1 hồ sơ `4 / 4`: kiểm tra đoạn highlight màu vàng khớp nguyên văn bio/tweet; bấm `Regenerate with AI` để thử gọi Live LLM tạo nháp mới.
   - Kiểm tra `P017` (Prompt Injection $\rightarrow$ `1 / 4`, DM rỗng), `P018` (Sparse $\rightarrow$ `0 / 4`, `INSUFFICIENT_EVIDENCE`), `P019` (`@arjun_infer` khóa nút gửi).
   - Bấm `Approve & Send` cho `@minh_quant` (chế độ `SANDBOX`, hoặc `LIVE_X` nếu đã đưa handle test vào whitelist) $\rightarrow$ mở lại kiểm tra cảnh báo khóa chống gửi đúp (`409`).
4. **Outreach Log, Reply & Calibration (`/ledger`, `/calibration`):**
   - Vào `/ledger`: kiểm tra header bảng 1 từ (`ID`, `Candidate`, `Message`, `Channel`, `Reply`, `Actions`), bấm `Log Reply` $\rightarrow$ hiện badge `URGENT`, mở `Audit Trail`, bấm `Mark Handled`.
   - Vào `/calibration`: đối chiếu `AI Score` (từ Live LLM) với `Ref Score`.
   - Chuyển đổi ngôn ngữ `EN` $\leftrightarrow$ `VI` trên menu góc phải trên.

---

## 7. Bộ Kiểm thử Tự động (Chạy lại bất kỳ lúc nào)

Các bộ test này chạy hoàn toàn cô lập (dùng `sqlite:///:memory:` và `outreach_e2e.db` ở cổng `3100`/`8001`), **không ghi đè** dữ liệu test tay của bạn trên `outreach.db` và **không tốn tiền API**:

```powershell
# Toàn bộ 39 tests Backend (Unit + API Integration + Contracts + Reset/X-Client Tools)
python -m pytest backend/tests/ -v

# Full Quality Gate 2 tầng (6 Contract Tests + 9 Playwright Browser E2E Specs)
powershell -ExecutionPolicy Bypass -File tests/manual/test-all.ps1
```

