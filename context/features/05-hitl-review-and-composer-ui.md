# Feature Spec 05: Human-in-the-Loop Review Workspace & Inline Composer
*(WBS Task 5 / Module 3: Human-in-the-Loop UI)*

---

## 1. Design Thinking: Thấu cảm, Định nghĩa & Ý tưởng hóa (Empathize, Define, Ideate)

### A. Empathize (Thấu cảm người dùng)
1. **Investment Associate / Partner tại GenAI Fund (Người dùng vận hành):**
   - *Áp lực duyệt hàng loạt:* Phải duyệt 20–50 hồ sơ mỗi ngày. Nếu mỗi hồ sơ phải mở modal hoặc chuyển trang thì sẽ cực kỳ mệt mỏi (*cognitive fatigue*).
   - *Nhu cầu xác thực nhanh:* Không muốn đọc lại toàn bộ bài tweet dài của founder để kiểm tra xem AI trích đúng hay sai. Họ cần nhìn thấy đoạn trích dẫn được tô sáng ngay lập tức.
   - *Nhu cầu cá nhân hóa:* Thường muốn chèn thêm một câu bông đùa hoặc lời mời cà phê cụ thể vào cuối tin nhắn (*"P.S. Sắp tới mình có ra Hà Nội, hẹn cafe nhé!"*).
2. **Hiring Committee / Giám khảo bài test:**
   - Muốn thấy rõ chốt chặn kiểm duyệt của con người: không có chuyện AI tự tiện gửi tin nhắn khi chưa được duyệt.
   - Thấy rõ sự phân biệt giữa các ca: High Fit (Score 4), Noise (Score 1), Sparse (Needs Person), Blocked (Closed DM).

### B. Define (Định nghĩa bài toán & HMW)
- **Tuyên ngôn vấn đề (POV):**
  > *"Đội ngũ đầu tư cần một không gian làm việc tập trung, tốc độ cao để thẩm định lý do phù hợp của AI, kiểm chứng bằng chứng trong nháy mắt và chỉnh sửa tin nhắn trực tiếp trước khi phê duyệt gửi đi với sự tự tin 100%."*
- **3 Câu hỏi cốt lõi (How Might We):**
  - **HMW-1 (Glanceable Verification):** Làm thế nào để người duyệt kiểm chứng bằng chứng AI trích xuất chỉ trong 1 giây mà không phải dò từng chữ trong tweet?
  - **HMW-2 (Frictionless Editing):** Làm thế nào để việc chỉnh sửa và gửi tin nhắn diễn ra mượt mà, tự động chuyển ứng viên tiếp theo sau mỗi quyết định?
  - **HMW-3 (Clear Boundary States):** Làm thế nào để hiển thị rõ ràng các trạng thái biên (hồ sơ rỗng, khóa DM, lỗi gọi AI) mà không làm người dùng bối rối?

### C. Ideate (Ý tưởng hóa giải pháp)
1. **Bố cục Chia đôi Màn hình (Split-Pane Master-Detail Workspace):**
   - Cột trái: Danh sách ứng viên theo bộ lọc (Match, Low Fit, Needs Human, Already Contacted).
   - Cột phải: Toàn bộ thông tin chi tiết (Why They Fit, Bio, Recent Tweets với Highlight màu vàng, và Khung soạn thảo DM trực tiếp).
2. **Visual Evidence Highlighter:**
   - Tự động tìm chuỗi `evidence_snippet` trong văn bản tweet và bọc thẻ `<mark class="bg-amber-100 font-semibold">` để nổi bật thị giác.
3. **Thao tác 1 Chạm Chuyển Hồ sơ:**
   - Bấm `[Reject]` hoặc `[Approve & Send]` sẽ cập nhật trạng thái và tự động chọn ngay ứng viên tiếp theo trong hàng đợi.

---

## 2. Mục tiêu cốt lõi (Core Purpose)
Cung cấp cho đội ngũ đầu tư của GenAI Fund một không gian làm việc trực quan (*Review Workspace*) để kiểm duyệt ứng viên, kiểm chứng bằng chứng thực tế (*Visual Evidence Highlighting*), chỉnh sửa trực tiếp nội dung tin nhắn DM và bấm phê duyệt (*Approve & Send*) hoặc từ chối (*Reject*).

---

## 3. Yêu cầu từ Đề bài (Requirements from Prompt)
- Soạn thảo DM cá nhân hóa để con người xem xét và phê duyệt (*review and approve*).
- Cá nhân hóa phải dùng bằng chứng thật, cấm bịa đặt sự quen biết.
- Đội ngũ quỹ có thể tự sử dụng mà không cần lập trình viên ngồi cạnh.
- Hiển thị rõ các giới hạn và hành động bị chặn (*blocked actions*).

---

## 4. Thách thức Kỹ thuật ngầm (Under-the-hood Technical Challenges)
- **Kiểm chứng Bằng chứng tức thì (Glanceable Evidence Verification):** Người duyệt không muốn đọc đi đọc lại cả đoạn tweet dài để tìm xem AI lấy chi tiết đó từ đâu. Nếu không làm nổi bật đoạn trích dẫn, người duyệt sẽ mất niềm tin vào độ chính xác của AI.
- **Trải nghiệm Sửa tin nhắn (Inline Editing UX):** Cần lưu vết cả bản nháp gốc của AI (`draft_dm`) lẫn bản chỉnh sửa của con người (`edited_dm`) để sau này phân tích chất lượng prompt.
- **Xử lý các trạng thái biên trên giao diện:**
  - Ứng viên bị lỗi chấm điểm (`AI_FAILED`): Phải hiển thị nút **Thử lại (Retry)**, không được làm người duyệt nhầm là ứng viên bị từ chối.
  - Ứng viên hồ sơ rỗng (`INSUFFICIENT_EVIDENCE`): Phải cảnh báo rõ "Thiếu bằng chứng để cá nhân hóa" và khóa nút gửi.
  - Ứng viên khóa DM (`SEND_BLOCKED`): Phải cảnh báo rõ "Khóa DM trên X".

---

## 5. Phân tích Đánh đổi Kỹ thuật (Trade-off Analysis)

| Hướng tiếp cận | Ưu điểm | Nhược điểm / Rủi ro | Quyết định & Lý do |
| :--- | :--- | :--- | :--- |
| **Cách tiếp cận A: Popup Modal nhiều bước (Multi-step Wizard)** | Dễ thiết kế từng bước riêng rẽ. | - Rất tốn thao tác: Để duyệt 20 ứng viên phải mở/đóng modal 40–60 lần.<br>- Che khuất thông tin nền, gây mệt mỏi cho người vận hành. | ❌ **LOẠI BỎ** |
| **Cách tiếp cận B: Bảng xem trước chỉ đọc (Read-only Preview Table)** | Hiển thị được nhiều dòng cùng lúc. | - Không cho phép chỉnh sửa văn bản trực tiếp.<br>- Phải mở trang mới mỗi khi muốn sửa một câu DM. | ❌ **LOẠI BỎ** |
| **Cách tiếp cận C (ĐƯỢC CHỌN): Split-Pane Master-Detail Review Workspace (Danh sách bên trái, Chi tiết & Soạn thảo bên phải)** | - **Duyệt siêu tốc:** Chọn ứng viên bên trái, toàn bộ Bio, Tweet, Bằng chứng tô sáng và Khung soạn thảo hiện ra ngay bên phải.<br>- **Tô sáng bằng chứng trực quan:** Tự động highlight đoạn văn bản trong Tweet trùng với `evidence_snippet`.<br>- **Phím tắt / Thao tác 1 chạm:** Bấm [Reject] hoặc [Approve & Send] tự động chuyển sang ứng viên kế tiếp. | Đòi hỏi thiết kế giao diện đồng bộ trạng thái mượt mà (responsive state sync). |  **CHỌN LỰA** (Tối ưu hóa năng suất vận hành thực tế cho VC team). |

---

## 6. Ràng buộc & Điều kiện bất biến (What Must Be True)
1. **Chốt chặn Phê duyệt:** Không có bất kỳ cơ chế tự động gửi nào chạy ngầm nếu chưa có cú click chuột rõ ràng của người dùng vào nút **[Approve & Send]**.
2. **Bảo tồn nội dung chỉnh sửa:** Nếu người dùng đã gõ sửa lại tin nhắn trong ô soạn thảo, khi gửi đi hệ thống bắt buộc phải gửi nội dung đã sửa (`edited_dm`), không gửi bản nháp cũ.
3. **Hiển thị rõ nút Retry khi lỗi:** Mọi hồ sơ có trạng thái `AI_FAILED` phải có nút `[Retry AI Evaluation]` màu vàng/cam nổi bật.

---

## 7. Đặc tả Kỹ thuật chi tiết (Technical Specification)

### Bố cục Giao diện (Layout Blueprint):
```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ [GenAI Fund Logo]  Outreach Workspace   [Upload CSV] [Load Seed Pack]   (User: Partner)│
├───────────────────────────────────┬──────────────────────────────────────────────┤
│ BỘ LỌC & DANH SÁCH ỨNG VIÊN (Trái)│ CHI TIẾT & SOẠN THẢO DM (Phải)               │
│ [All] [Match (12)] [Low Fit] [Blocked]│ @minh_quant - Minh Nguyen (Hanoi, Vietnam)   │
│                                   │ Score: [4/4 HIGH FIT]  Segment: AI Infra     │
│ 1. @minh_quant       [Score 4]    │ ──────────────────────────────────────────── │
│ 2. @dr_somchai_ai    [Score 4]    │ WHY THEY FIT:                                │
│ 3. @wei_devtools     [Score 4]    │ Founder xây dựng engine suy luận LLM cho telco│
│ 4. @kevin_wrapper    [Score 2]    │ ──────────────────────────────────────────── │
│ 5. @override_bot99   [Score 1]    │ RECENT TWEET & EVIDENCE:                     │
│ 6. @ghost_builder    [Needs Human]│ "...AWQ-W4A8 speculative decoding kernel for │
│ 7. @arjun_infer      [DM Closed]  │  L40S GPUs (tensoredge-vn/edge-vllm)..."     │
│                                   │ ──────────────────────────────────────────── │
│                                   │ PERSONALIZED DM COMPOSER:                    │
│                                   │ ┌──────────────────────────────────────────┐ │
│                                   │ │ Hi Minh — saw your post on AWQ-W4A8     │ │
│                                   │ │ speculative decoding for L40S GPUs.      │ │
│                                   │ │ We back AI infra builders at GenAI Fund  │ │
│                                   │ │ and would love to hear about adoption... │ │
│                                   │ └──────────────────────────────────────────┘ │
│                                   │ [Regenerate]     [Reject]   [Approve & Send] │
└───────────────────────────────────┴──────────────────────────────────────────────┘
```

---

## 8. Kịch bản Kiểm thử & Nghiệm thu (Acceptance Criteria)
- [ ] **Test Evidence Highlight:** Mở hồ sơ `P002`, đoạn văn bản *"AWQ-W4A8 speculative decoding kernel"* trong Recent Tweets được tô nền màu vàng/xanh rõ rệt.
- [ ] **Test Edit & Send:** Người dùng gõ thêm dòng *"P.S. Coffee in Hanoi next week?"* vào ô soạn thảo, bấm [Approve & Send] $\rightarrow$ trong `outreach_ledger` lưu đúng nội dung đã chỉnh sửa.
- [ ] **Test Blocked DM Warning:** Mở hồ sơ `P019`, hiển thị badge đỏ *"DMs Closed by User"*, nút [Approve & Send] chuyển thành trạng thái bị vô hiệu hóa kèm lý do.
