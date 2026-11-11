# Feature Spec 07: Verification, Automated Testing & Turnkey Handover (< 15 mins)
*(WBS Task 7 / Turnkey Handover)*

---

## 1. Design Thinking: Thấu cảm, Định nghĩa & Ý tưởng hóa (Empathize, Define, Ideate)

### A. Empathize (Thấu cảm người dùng)
1. **Hiring Committee / Giám khảo bài test (Người đánh giá):**
   - *Áp lực thời gian:* Họ phải chấm hàng chục bài thi. Nếu một dự án mất quá 15 phút cài đặt hoặc văng lỗi dependency trên Windows/macOS, bài thi sẽ bị đánh trượt ngay lập tức (*"setup in under 15 minutes"*).
   - *Kỳ vọng:* Mở file `README.md` lên là thấy ngay 3 bước chạy đơn giản, chạy lệnh test `pytest` là thấy màu xanh (*All tests passed*), có sẵn tài liệu 1 trang giải thích rõ ràng các quyết định kỹ thuật và bảng chi phí.
2. **VC Partners (Người tiếp nhận bàn giao):**
   - Cần một bản tóm tắt kiến trúc trung thực, không giấu diếm các giới hạn của hệ thống, chỉ rõ lộ trình nâng cấp tiếp theo (*What comes next*).

### B. Define (Định nghĩa bài toán & HMW)
- **Tuyên ngôn vấn đề (POV):**
  > *"Người chấm thi và đội ngũ kỹ thuật cần một bộ bàn giao hoàn chỉnh, sẵn sàng vận hành trên máy mới trong dưới 15 phút, được kiểm chứng bởi bộ test tự động độc lập 100% và một tài liệu tóm tắt kỹ thuật sắc sảo."*
- **3 Câu hỏi cốt lõi (How Might We):**
  - **HMW-1 (Zero-Friction Clean Machine Runnability):** Làm thế nào để đảm bảo bất kỳ ai clone repo về cũng có thể khởi chạy thành công ngay lần đầu tiên trong < 5 phút?
  - **HMW-2 (Hermetic Automated Tests):** Làm thế nào để bộ test `pytest` kiểm tra được toàn bộ 7 điều kiện bất biến mà không bắt người chấm phải có kết nối Internet hay API key trả phí?
  - **HMW-3 (Compelling 1-Page Write-up):** Làm thế nào để truyền tải trọn vẹn tư duy Forward Deployed Engineer (kiến trúc, đánh đổi, chi phí, độ tin cậy) chỉ trong đúng 1 trang tài liệu?

### C. Ideate (Ý tưởng hóa giải pháp)
1. **Quy trình Khởi chạy 3 Bước Tối giản (3-Step Quickstart):**
   - Không bắt cài Docker daemon cồng kềnh: Chỉ cần Python 3.10+ tiêu chuẩn và `pip install -r requirements.txt`.
   - File `.env.example` cấu hình sẵn chế độ Sandbox Mode an toàn.
2. **Bộ Test Tự động Độc lập (Hermetic Pytest Suite):**
   - Toàn bộ test case dùng mock LLM & mock Dispatcher để test logic cốt lõi (Idempotency, Prompt Injection, Closed DMs, State Machine) mà không tốn tiền API hay phụ thuộc mạng ngoài.
3. **Bản Bàn giao 1 Trang Chuẩn mực (`ARCHITECTURE_AND_WRITEUP.md`):**
   - Cấu trúc 5 phần cô đọng: *Approach & Architecture*, *Key Trade-offs*, *What Comes Next*, *Cost Analysis*, *AI Tooling & Verification*.

---

## 2. Mục tiêu cốt lõi (Core Purpose)
Đảm bảo chất lượng hệ thống thông qua bộ kiểm thử tự động toàn diện, cung cấp tài liệu cài đặt chuẩn xác giúp người đánh giá có thể khởi chạy trên một máy tính hoàn toàn mới trong **dưới 15 phút**, và hoàn thiện bộ tài liệu bàn giao bắt buộc (Mã nguồn, Video Demo 3–5 phút, One-page write-up).

---

## 3. Yêu cầu từ Đề bài (Requirements from Prompt)
- Người đánh giá có thể tự chạy công cụ mà không cần bạn ngồi cạnh; cài đặt hoàn tất dưới 15 phút.
- Bộ sản phẩm bàn giao đầy đủ:
  1. Working Prototype (URL hoặc Repo cài đặt < 15 phút).
  2. Video demo (3–5 phút).
  3. One-page write-up.
- Nêu rõ các công cụ trả phí đã dùng và ước tính chi phí vận hành hàng tháng.

---

## 4. Thách thức Kỹ thuật ngầm (Under-the-hood Technical Challenges)
- **Rào cản Môi trường (Environment Friction):** Các thư viện C-extension (như `psycopg2` hay các bản build của `sqlite3` cũ) thường gây lỗi biên dịch trên máy Windows của giám khảo. Do đó backend cần dùng thư viện thuần Python (`SQLAlchemy`, `FastAPI`, `Pydantic v2`).
- **Phụ thuộc API Key trong lúc Chạy Test:** Nếu chạy `pytest` mà yêu cầu có `X_BEARER_TOKEN` thật thì bài thi sẽ bị crash ngay trên máy giám khảo.

---

## 5. Phân tích Đánh đổi Kỹ thuật (Trade-off Analysis)

| Hướng tiếp cận | Ưu điểm | Nhược điểm / Rủi ro | Quyết định & Lý do |
| :--- | :--- | :--- | :--- |
| **Cách tiếp cận A: Đóng gói Docker Compose đa container (App + DB + Redis + Nginx)** | Đảm bảo đồng nhất môi trường 100%. | - Bắt người chấm phải cài Docker Desktop (nhiều GB, nặng máy, cần bật WSL2 trên Windows).<br>- Dễ bị lỗi cổng port bị chiếm dụng (port 80/8080/5432).<br>- Vượt quá thời gian 15 phút. | ❌ **LOẠI BỎ** |
| **Cách tiếp cận B: Native Python Standard Virtualenv + Single Command Start** | - Cực nhẹ, cài đặt trong 2 phút.<br>- Chạy mượt mà trên mọi hệ điều hành (Windows PowerShell, macOS Terminal, Ubuntu Linux).<br>- Người chấm kiểm soát trực tiếp mã nguồn. | Cần viết hướng dẫn rõ ràng cho cả Windows và Unix. |  **CHỌN LỰA** (Lựa chọn thông minh nhất của FDE). |

---

## 6. Ràng buộc & Điều kiện bất biến (What Must Be True)
1. **Turnkey Setup < 15 Phút:** Một người dùng bất kỳ làm theo `README.md` từ thư mục rỗng phải khởi động được web và nạp seed data thành công trong dưới 15 phút.
2. **100% Hermetic Pytest Suite:** Chạy lệnh `pytest` không yêu cầu kết nối Internet và không yêu cầu điền API key thật nhưng vẫn chứng minh được đầy đủ 7 invariants.
3. **Minh bạch Chi phí:** Bản write-up phải có bảng tính chi phí định lượng thực tế (~$0.02 / 100 hồ sơ).

---

## 7. Đặc tả Kỹ thuật chi tiết (Technical Specification)

### Cấu trúc Bộ Kiểm thử Tự động (`backend/tests/`):
- `test_ingestion.py`: Kiểm tra chuẩn hóa handle, nạp file seed, và lọc trùng lặp in-batch (`P002` vs `P020`).
- `test_state_machine.py`: Kiểm tra chuyển đổi 9 trạng thái và cơ chế chống click đúp (Idempotency).
- `test_ai_scorer.py`: Kiểm tra phòng vệ Prompt Injection trên `P017`, kiểm tra hồ sơ rỗng trên `P018`, và kiểm tra Evidence Grounding.
- `test_dispatcher.py`: Kiểm tra bảo vệ khóa DM trên `P019`, kiểm tra Safety Whitelist trong chế độ Live X, và kiểm tra ghi nhận vào `outreach_ledger`.
- `test_auth.py`: Kiểm tra chặn truy cập khi chưa login (`401`) và xác thực JWT token.

### Đề cương Bản Bàn giao 1 Trang (`ARCHITECTURE_AND_WRITEUP.md`):
1. **Approach & System Architecture:** Sơ đồ Golden Flow, State Machine, Dual Queue Engine.
2. **Key Engineering Trade-offs:** Phân tích vì sao chọn Dual-Mode (Sandbox vs Live X), SQLite WAL persistent thay vì Redis/Postgres, và Structured Output thay vì regex.
3. **What Comes Next:** Lộ trình phát triển Production (Webhook Account Activity API của X, Multi-tenant cho nhiều quỹ, AI Voice DM).
4. **Operational Cost Analysis:** Bảng tính chi phí LLM token (~$0.0005/call), chi phí server ($5/mo), chi phí X API ($0 ở Sandbox, $100 ở Basic).
5. **AI Safety & Evidence Verification:** Quy tắc Fortified Delimiters và cơ chế Evidence Grounding Guard.

---

## 8. Kịch bản Kiểm thử & Nghiệm thu (Acceptance Criteria)
- [ ] **Test Clean Machine Runnability:** Kiểm thử chạy lại quy trình cài đặt từ đầu theo đúng hướng dẫn `README.md` trên PowerShell sạch hoàn thành trong < 8 phút.
- [ ] **Test Pytest Suite Execution:** Chạy lệnh `pytest backend/tests/` $\rightarrow$ 100% test case pass xanh (0 failure, 0 error).
- [ ] **Test Deliverable Completeness:** Có đầy đủ: Mã nguồn sạch, Seed data thực tế, `ARCHITECTURE_AND_WRITEUP.md`, và link Video Demo.

