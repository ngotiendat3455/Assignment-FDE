# Feature Spec 06: Outreach Ledger, Inbox Tracker & Calibration Matrix
*(WBS Task 6 / Module 6: Outreach Ledger & Dashboard)*

---

## 1. Design Thinking: Thấu cảm, Định nghĩa & Ý tưởng hóa (Empathize, Define, Ideate)

### A. Empathize (Thấu cảm người dùng)
1. **VC Partners (Người quản lý cấp cao):**
   - Cần nhìn thấy bức tranh tổng thể: Quỹ đã tiếp cận bao nhiêu founder? Tỷ lệ phản hồi ra sao? Ai đã trả lời và cuộc trò chuyện nào cần đối tác vào tiếp quản ngay lập tức?
   - Cần chứng minh chất lượng AI: Muốn biết thuật toán AI chấm điểm có tương đồng với khẩu vị đầu tư thực tế của quỹ hay không.
2. **Hiring Committee / Giám khảo bài test:**
   - Đề bài yêu cầu: *"shows us what was sent, who replied and what needs our attention"*.
   - Muốn kiểm tra gói đối chiếu điểm chuẩn (`fund_reference_scores.csv`) để xem ứng viên FDE đo lường và kiểm soát độ chính xác của AI như thế nào.

### B. Define (Định nghĩa bài toán & HMW)
- **Tuyên ngôn vấn đề (POV):**
  > *"Ban lãnh đạo quỹ và người vận hành cần một sổ cái bất biến để theo dõi toàn bộ dấu vết tiếp cận, một trung tâm xử lý phản hồi khẩn cấp (Needs Attention), và một bảng đối chiếu hiệu năng AI so với điểm chuẩn để luôn kiểm soát được chiến dịch."*
- **3 Câu hỏi cốt lõi (How Might We):**
  - **HMW-1 (Full Traceability):** Làm thế nào để lưu vết chính xác nội dung từng tin nhắn đã gửi, thời gian gửi và người duyệt gửi mà không thể bị sửa xóa?
  - **HMW-2 (Actionable Lead Follow-up):** Làm thế nào để đảm bảo không một phản hồi tích cực nào của founder bị bỏ quên?
  - **HMW-3 (Proof of Alignment):** Làm thế nào để trực quan hóa mức độ ăn khớp giữa AI Scorer và điểm đánh giá của đối tác quỹ?

### C. Ideate (Ý tưởng hóa giải pháp)
1. **Sổ cái Chiến dịch Bất biến (Immutable Outreach Ledger):**
   - Lưu trữ đầy đủ: Người gửi, thời gian, nội dung tin nhắn thực tế đã gửi (kể cả phần do con người sửa), chế độ Sandbox hay Live X.
2. **Trung tâm Phản hồi với Cờ Khẩn cấp (Needs Attention Triage):**
   - Hỗ trợ nút mô phỏng `[Record Founder Reply]` $\rightarrow$ tự động gắn cờ đỏ `NEEDS ATTENTION` kèm nút `[Mark Handled]`.
3. **Ma trận Hiệu chuẩn Đối tác (Partner Calibration Matrix):**
   - Tự động so sánh điểm số thực tế AI chấm với `fund_reference_scores.csv`, tính toán tỷ lệ tương đồng (*Alignment Rate %*) và hiển thị bảng phân tích chi tiết từng ca.

---

## 2. Mục tiêu cốt lõi (Core Purpose)
Cung cấp Sổ cái chiến dịch (*Outreach Ledger*) minh bạch, theo dõi chi tiết tin nhắn đã gửi, trạng thái phản hồi (*Replied*), gắn cờ các cuộc hội thoại khẩn cấp cần đối tác xử lý (*Needs Attention*), và bảng đối chiếu độ chính xác chấm điểm của AI (*Calibration Matrix*) so với điểm chuẩn của quỹ.

---

## 3. Yêu cầu từ Đề bài (Requirements from Prompt)
- Hiển thị rõ ràng những gì đã được gửi, ai đã phản hồi và những gì cần sự chú ý của chúng tôi (*"shows us what was sent, who replied and what needs our attention"*).
- Đo lường và giải thích cách bạn sử dụng công cụ AI và kiểm chứng đầu ra của chúng.

---

## 4. Thách thức Kỹ thuật ngầm (Under-the-hood Technical Challenges)
- **Cơ chế Phát hiện Phản hồi (Reply Detection Mechanism):**
  - Webhook của X (Account Activity API) đòi hỏi đăng ký gói Enterprise phức tạp và server phải có public IP / SSL webhook URL hợp lệ.
  - Khi chạy localhost hoặc bản demo take-home, giám khảo không thể thiết lập webhook X. Do đó, cần cơ chế đồng bộ linh hoạt: hỗ trợ cả nút mô phỏng **[Mark as Replied]** (kèm nhập nội dung phản hồi) và endpoint sync từ API.
- **Hiện tượng Bỏ sót Khách hàng tiềm năng (Cold Leads):** Sau khi founder trả lời, nếu không có cờ nổi bật (*Needs Attention*), đối tác của quỹ sẽ không biết để vào chat tiếp.

---

## 5. Phân tích Đánh đổi Kỹ thuật (Trade-off Analysis)

| Hướng tiếp cận | Ưu điểm | Nhược điểm / Rủi ro | Quyết định & Lý do |
| :--- | :--- | :--- | :--- |
| **Cách tiếp cận A: Xây dựng Auto-Chatbot đa vòng (Multi-turn Auto-DM)** | Tự động trả lời founder. | - Cực kỳ nguy hiểm: Bot có thể hứa hẹn đầu tư sai sự thật hoặc phát ngôn bừa bãi làm hỏng uy tín của quỹ.<br>- Đề bài nêu rõ: *"get real conversations started"* (chỉ cần khơi mào cuộc hội thoại thực chất đầu tiên). | ❌ **LOẠI BỎ** |
| **Cách tiếp cận B: Chỉ xuất file CSV tĩnh (Static CSV Export)** | Dễ code nhất. | - Không có tính tương tác theo thời gian thực.<br>- Không giúp được HR/Partner biết ai đang cần phản hồi gấp. | ❌ **LOẠI BỎ** |
| **Cách tiếp cận C (ĐƯỢC CHỌN): Interactive CRM Ledger + Actionable "Needs Attention" Triage + Partner Calibration Benchmark** | - **Minh bạch 100%:** Bảng Ledger hiển thị rõ nội dung tin nhắn, giờ gửi, người gửi, chế độ Sandbox/Live.<br>- **Phản hồi 1-click:** Nút [Simulate/Record Reply] cho phép nhập nội dung trả lời của founder $\rightarrow$ kích hoạt cờ đỏ `NEEDS ATTENTION`.<br>- **Calibration Matrix:** Bảng so khớp tự động giữa điểm AI chấm và `fund_reference_scores.csv` để chứng minh độ chính xác của prompt trước ban giám khảo. | Cần thiết kế thêm tab Thống kê/Dashboard trong giao diện. |  **CHỌN LỰA** (Gây ấn tượng mạnh về tính hoàn thiện của sản phẩm). |

---

## 6. Ràng buộc & Điều kiện bất biến (What Must Be True)
1. **Lưu vết Bất biến (Immutable Sent Log):** Tin nhắn đã gửi đi không bao giờ được xóa hoặc ghi đè trong `outreach_ledger`.
2. **Cờ "Needs Attention":** Bất kỳ ứng viên nào có trạng thái `REPLIED` đều tự động kích hoạt `needs_attention = true` cho đến khi đối tác nhấn nút `[Mark Handled]`.
3. **Báo cáo Độ tin cậy AI:** Hệ thống hiển thị rõ tỷ lệ trùng khớp (Accuracy / Alignment %) giữa AI Scorer và điểm chuẩn trong gói dữ liệu.

---

## 7. Đặc tả Kỹ thuật chi tiết (Technical Specification)

### Các chỉ số KPI trên Dashboard:
- **Total Ingested:** Tổng số hồ sơ đã nạp vào hệ thống.
- **High-Signal Matches:** Số ứng viên đạt tiêu chí (Score 3 hoặc 4).
- **Outreach Dispatched:** Số lượng tin nhắn DM đã gửi thành công (`SENT`).
- **Replies Received:** Số lượng founder đã phản hồi (`REPLIED`).
- **Needs Attention:** Số cuộc hội thoại đang chờ đối tác quỹ trả lời.
- **Safety Blocks / Dedup Interceptions:** Số lần hệ thống bảo vệ quỹ khỏi việc gửi trùng hoặc gửi cho người khóa DM.

### Bảng Đối chiếu Calibration (`fund_reference_scores.csv`):
```text
┌──────────┬──────────────┬───────────────┬──────────┬───────────┬─────────────┐
│ Profile  │ Handle       │ Target Track  │ AI Score │ Ref Score │ Match Delta │
├──────────┼──────────────┼───────────────┼──────────┼───────────┼─────────────┤
│ P002     │ minh_quant   │ Infrastructure│    4     │     4     │ Exact Match │
│ P003     │ dr_somchai_ai│ Robotics      │    4     │     4     │ Exact Match │
│ P009     │ kevin_wrapper│ Applications  │    2     │     2     │ Exact Match │
│ P010     │ cryptoking_ai│ Noise         │    1     │     1     │ Exact Match │
│ P017     │ override_bot │ Adversarial   │    1     │     1     │ Defended    │
│ P018     │ ghost_builder│ Sparse        │    0     │     0     │ Flagged     │
└──────────┴──────────────┴───────────────┴──────────┴───────────┴─────────────┘
```

---

## 8. Kịch bản Kiểm thử & Nghiệm thu (Acceptance Criteria)
- [ ] **Test Seed History Display:** Khởi tạo DB $\rightarrow$ Dashboard hiển thị ngay 4 bản ghi lịch sử mẫu (`OUT-101` đến `OUT-104`).
- [ ] **Test Reply & Needs Attention:** Bấm [Record Reply] cho một ứng viên đang ở trạng thái `SENT` $\rightarrow$ trạng thái chuyển sang `REPLIED`, huy hiệu `NEEDS ATTENTION` màu đỏ sáng lên.
- [ ] **Test Mark Handled:** Bấm [Mark Handled] $\rightarrow$ tắt huy hiệu đỏ, chuyển về trạng thái bình thường.
- [ ] **Test Calibration Accuracy:** Mở tab Calibration, hệ thống tính toán và hiển thị độ tương đồng đạt > 85% so với điểm chuẩn của đối tác.
