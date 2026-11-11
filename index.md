Created 01-scouting-and-ingestion.md
Created 02-context-and-reason-generator.md
Created 03-state-machine-and-deduplication.md
Created 04-platform-compliance-and-queue.md
Created 05-hitl-review-and-composer-ui.md
Created 06-outreach-ledger-and-dashboard.md
Created 07-auth-security-and-handover.md
Ran verify files in d:\AssignmentFDE\context

Tôi đã khởi tạo và hoàn thiện trọn bộ hệ thống **AI Context & Steering Specs** tại [**`D:\AssignmentFDE\context`**](file:///d:/AssignmentFDE/context).

Mỗi tệp đặc tả tính năng trong `features/` đều được phân tích sâu theo đúng **5 module lõi** của bài toán, làm rõ **thách thức kỹ thuật ngầm (under-the-hood challenges)** và bảng **phân tích đánh đổi kỹ thuật (Trade-off Analysis: Phương án A vs B vs C)**.

---

### Tổng quan Kiến trúc Thư mục `context/`

```text
D:\AssignmentFDE\context\
├── project-overview.md     # Bản đồ định hướng, 7 điều kiện bất biến (What must be true) & Golden Flow
├── coding-standards.md     # Chuẩn code (Python/FastAPI, Next.js, SQLite WAL, bảo mật, Rate limit)
├── ai-interaction.md       # Quy tắc tác chiến cho AI Agent (Test-first, cập nhật tiến độ, chống hallucination)
├── current-feature.md      # Bảng trạng thái làm việc thời gian thực (Active Sprint & Checklist)
└── features/               # Đặc tả chi tiết từng lát cắt tính năng (Kèm Trade-off Analysis)
    ├── 01-scouting-and-ingestion.md          # Module 1: Scouting & Ingestion
    ├── 02-context-and-reason-generator.md    # Module 2: LLM Fit Scorer & Grounded DM Drafter
    ├── 03-state-machine-and-deduplication.md # Module 4: State Machine & Deduplication Engine
    ├── 04-platform-compliance-and-queue.md   # Module 5: Rate Limiting & Dual-Mode Dispatcher
    ├── 05-hitl-review-and-composer-ui.md     # Module 3: Review Workspace & Inline DM Composer
    ├── 06-outreach-ledger-and-dashboard.md   # Module 6: Outreach Ledger, Inbox & Calibration
    └── 07-auth-security-and-handover.md      # Module 7: JWT Auth, Pytest & Turnkey Setup < 15 mins
```

---

### Tóm tắt Ma trận Phân tích Đánh đổi Kỹ thuật (Trade-offs) trong từng Feature Spec

| Feature Spec | Thách thức kỹ thuật ngầm | Đánh đổi kỹ thuật (Trade-off Analysis) | Quyết định được chọn |
| :--- | :--- | :--- | :--- |
| [**`01-scouting-and-ingestion.md`**](file:///d:/AssignmentFDE/context/features/01-scouting-and-ingestion.md) *(Scouting & Ingestion)* | Cấm scraping trái phép; X API Free tier không cho search; X API Basic tốn $100/tháng và giới hạn khắt khe. | **Ép dùng Live API (Bị phụ thuộc tiền/quota)** vs **Chỉ Mock dữ liệu trong RAM (Red flag)** vs **Dual-Source Ingestion Engine (Seed Pack + Live X Lookup)**. | **Dual-Source Engine:** Cung cấp sẵn CSV 20 hồ sơ ĐNÁ chạy 0-tốn-tiền ngay lập tức, nhưng sẵn sàng kết nối Live API nếu người chấm nhập key. |
| [**`02-context-and-reason-generator.md`**](file:///d:/AssignmentFDE/context/features/02-context-and-reason-generator.md) *(Fit Scorer & DM Drafter)* | Prompt Injection (`P017`); Bịa đặt sự quen biết khi hồ sơ rỗng (`P018`); Chi phí & độ trễ LLM; Lỗi JSON format. | **Mô hình khủng (GPT-4o/Sonnet) sinh tự do (Đắt, dễ hallucinate)** vs **Regex từ khóa (Ngây thơ, không hiểu ngữ cảnh)** vs **Compact Fast LLM (Gemini Flash / GPT-4o-mini) + Fortified Delimiters + Grounding Check**. | **Compact Fast LLM + Structured Output:** Chi phí < $0.0005/hồ sơ, tốc độ < 2s; đóng gói input trong thẻ bảo vệ để chống Prompt Injection; kiểm tra trích dẫn thật. |
| [**`03-state-machine-and-deduplication.md`**](file:///d:/AssignmentFDE/context/features/03-state-machine-and-deduplication.md) *(State Machine & De-dupe)* | Gửi trùng do click đúp; Trùng lặp xuyên chiến dịch (đã gửi từ các tuần trước); Ràng buộc không dùng In-memory DB. | **Client-side check (Red flag nghiêm trọng)** vs **Redis Distributed Lock (Nặng nề, khó setup < 15p)** vs **SQLite Persistent Engine + DB-Level UNIQUE Constraints + Atomic Transactions**. | **SQLite Persistent + UNIQUE constraints:** Khóa `UNIQUE` trên `handle` và `x_user_id` ở cả bảng `candidates` và `outreach_ledger`; đảm bảo 100% không bao giờ gửi trùng cấp DB. |
| [**`04-platform-compliance-and-queue.md`**](file:///d:/AssignmentFDE/context/features/04-platform-compliance-and-queue.md) *(Rate Limiting & Queue)* | Nguy cơ khóa tài khoản X nếu gửi burst; Người chấm thử nghiệm gửi nhầm cho người lạ; Độ phức tạp hạ tầng queue. | **Celery + RabbitMQ/Redis (Nặng, phá vỡ setup < 15p)** vs **Gọi HTTP đồng bộ (Treo đơ UI)** vs **SQLite Persistent Queue + In-process Asyncio Worker + Token Bucket + Safety Whitelist**. | **In-process Queue + Safety Whitelist:** Queue lưu trong SQLite `job_queue`; worker chạy nền an toàn; chế độ Live X chỉ gửi cho tài khoản trong `ALLOWED_TEST_HANDLES`. |
| [**`05-hitl-review-and-composer-ui.md`**](file:///d:/AssignmentFDE/context/features/05-hitl-review-and-composer-ui.md) *(HITL Review Workspace)* | Người duyệt mất niềm tin nếu không thấy rõ bằng chứng; Trải nghiệm sửa tin nhắn cồng kềnh; Trạng thái lỗi không rõ ràng. | **Modal Popup nhiều bước (Tốn click)** vs **Bảng Preview chỉ đọc (Không sửa được tin)** vs **Split-Pane Master-Detail Review Workspace**. | **Split-Pane Workspace:** Bên trái là danh sách ứng viên có nhãn phân loại; bên phải là chi tiết, tô sáng bằng chứng trực quan (`Visual Evidence Highlighting`), ô sửa DM và nút Reject / Send. |
| [**`06-outreach-ledger-and-dashboard.md`**](file:///d:/AssignmentFDE/context/features/06-outreach-ledger-and-dashboard.md) *(Ledger & Dashboard)* | X Webhook khó setup trên localhost; Bỏ sót hội thoại khi founder phản hồi; Cần chứng minh chất lượng AI output. | **Auto-Chatbot đa vòng (Nguy hiểm, sai đề bài)** vs **File CSV tĩnh (Thiếu tương tác)** vs **Interactive CRM Ledger + Actionable "Needs Attention" Triage + Calibration Benchmark**. | **Interactive Ledger + Calibration Matrix:** Cho phép ghi nhận phản hồi, bật cờ đỏ `NEEDS ATTENTION` cho Partner; có bảng so khớp tự động với `fund_reference_scores.csv`. |
| [**`07-auth-security-and-handover.md`**](file:///d:/AssignmentFDE/context/features/07-auth-security-and-handover.md) *(Auth, Security & Handover)* | Người chấm vướng lỗi cài đặt môi trường; Lộ API key; Yêu cầu test chạy độc lập không cần internet. | **OAuth2 bên thứ 3 (Bắt người chấm tạo OAuth client)** vs **Không làm Login (Red flag bảo mật)** vs **Lightweight JWT Auth + Seeded Partner Account + 1-Click Demo Login**. | **JWT Auth + 1-Click Demo Login:** Vừa bảo mật tuyệt đối API, vừa cho phép người chấm bấm 1 click vào thẳng hệ thống mà không cần đăng ký tài khoản. |

---

Toàn bộ ngữ cảnh định hướng và các bản đặc tả chi tiết đã sẵn sàng. 
Bạn có muốn chúng ta bắt tay vào triển khai **Task 1 & Task 2 (Khởi tạo Backend, Database Models, Seed Data Script và Viết Unit Tests)** ngay bây giờ không?