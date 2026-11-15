# Feature Spec 05: Human-in-the-Loop Review Workspace & Inline Composer
*(WBS Task 5 / Module 3: Human-in-the-Loop UI)*

---

## 1. Design Thinking: Thấu cảm, Định nghĩa & Ý tưởng hóa (Empathize, Define, Ideate)

### A. Empathize (Thấu cảm người dùng)
1. **Investment Associate / Partner tại X-Scout AI (Người dùng vận hành):**
   - *Nhu cầu nhìn tổng quan:* Muốn có một bảng danh sách dạng Table rộng rãi, thoáng đãng để quét nhanh toàn bộ ứng viên, lọc theo điểm số và tìm kiếm tức thì.
   - *Nhu cầu không gian tập trung (Deep Focus):* Khi đọc bằng chứng và sửa câu chữ tin nhắn DM, họ cần một khung làm việc rộng rãi, không bị gò bó trong một cột nhỏ hẹp bên phải như cách chia đôi màn hình (*split-pane*).
   - *Thao tác nhanh gọn:* Có thể bấm xóa/từ chối ứng viên ngay từ bảng, hoặc mở modal xem chi tiết đầy đủ ngữ cảnh rồi mới bấm duyệt gửi.
2. **Hiring Committee / Giám khảo bài test:**
   - Đề bài yêu cầu: *"Human in the loop review and approve"*, *"shows evidence and reasons for fit"*, *"make limitations and blocked actions clear"*.
   - Đánh giá cao giao diện có tổ chức: Bảng danh sách rõ ràng, bộ lọc thông minh, và modal kiểm chứng bằng chứng trực quan.

### B. Define (Định nghĩa bài toán & HMW)
- **Tuyên ngôn vấn đề (POV):**
  > *"Đội ngũ đầu tư cần một giao diện dạng Bảng (Table-first) trực quan, có bộ tìm kiếm và lọc đa tiêu chí để quản lý toàn diện danh sách ứng viên, kết hợp với Modal Kiểm duyệt Chuyên sâu để kiểm chứng bằng chứng và tinh chỉnh tin nhắn DM với sự tập trung cao nhất."*
- **3 Câu hỏi cốt lõi (How Might We):**
  - **HMW-1 (Search & Triage):** Làm thế nào để người duyệt tìm kiếm và lọc ra các ứng viên điểm cao (Score 3–4) hoặc ứng viên bị lỗi/khóa DM trong 1 cú click?
  - **HMW-2 (Glanceable Evidence in Modal):** Làm thế nào để trong Modal, người duyệt kiểm chứng được ngay câu tweet AI đã trích xuất mà không phải căng mắt đọc lại toàn bộ bài viết?
  - **HMW-3 (Frictionless Actions):** Làm thế nào để người dùng có thể duyệt nhanh từng người, từ chối ngay ngoài bảng hoặc chuyển tiếp mượt mà giữa các hồ sơ trong modal?

### C. Ideate (Ý tưởng hóa giải pháp)
1. **Bố cục Bảng Dữ liệu Toàn cảnh (Table-First Workspace Canvas):**
   - Thay vì chia đôi màn hình làm chật chội không gian, toàn bộ diện tích trang được dùng cho **Bảng Ứng viên Chuẩn mực** kèm thanh tìm kiếm và bộ lọc trạng thái.
   - Các cột thông tin: Tên & Handle, Khu vực / Phân khúc, Điểm số AI (Score Pill), Trạng thái hệ thống (Status Badge), Cột Hành động (`[👁️ Xem & Duyệt]`, `[🗑️ Loại bỏ]`).
2. **Modal Kiểm duyệt & Soạn thảo Chuyên sâu (Review & Composer Modal):**
   - Khi bấm `[👁️ Xem & Duyệt]`, mở Modal tập trung:
     - Bên trái/trên: Bio, Tweet gần nhất có **Tô sáng bằng chứng màu hổ phách** (`evidence_snippet`), và Lý do phù hợp (*Why They Fit*).
     - Bên phải/dưới: Ô soạn thảo DM cá nhân hóa trực tiếp (`draft_dm`), Bộ đếm ký tự, Nút `[Tạo lại bằng AI]`, Nút `[Từ chối]`, và Nút `[Phê duyệt & Gửi]`.
3. **Thao tác Nhanh Trực tiếp từ Bảng:**
   - Cho phép bấm icon thùng rác `[🗑️]` để loại bỏ ứng viên không phù hợp ngay tại danh sách mà không cần mất công mở modal.

---

## 2. Mục tiêu cốt lõi (Core Purpose)
Cung cấp cho đội ngũ đầu tư của X-Scout AI một không gian làm việc dạng bảng (Table Workspace) để tìm kiếm, phân loại ứng viên, và một Modal kiểm duyệt chuyên sâu để kiểm chứng bằng chứng thực tế (*Visual Evidence Highlighting*), chỉnh sửa trực tiếp nội dung tin nhắn DM và bấm phê duyệt (*Approve & Send*) hoặc từ chối (*Reject*).

---

## 3. Yêu cầu từ Đề bài (Requirements from Prompt)
- Soạn thảo DM cá nhân hóa để con người xem xét và phê duyệt (*review and approve*).
- Cá nhân hóa phải dùng bằng chứng thật, cấm bịa đặt sự quen biết.
- Đội ngũ quỹ có thể tự sử dụng mà không cần lập trình viên ngồi cạnh.
- Hiển thị rõ các giới hạn và hành động bị chặn (*blocked actions*).

---

## 4. Thách thức Kỹ thuật ngầm (Under-the-hood Technical Challenges)
- **Tối ưu Không gian Hiển thị trên Màn hình Laptop (13–14 inches):** Mô hình Split-Pane cũ khiến bảng danh sách bị co cụm chỉ còn vài chục ký tự, che khuất thông tin phân khúc và địa điểm. Mô hình Bảng + Modal giải phóng 100% chiều ngang màn hình.
- **Tô sáng Dẫn chứng Nguyên văn (Exact Substring Highlighting):** Cần thuật toán tìm kiếm chuỗi con `evidence_snippet` trong chuỗi `recent_tweets` không phân biệt hoa thường và bọc thẻ `<mark>` an toàn.
- **Đồng bộ Dữ liệu sau Hành động (State Sync):** Khi người dùng bấm `Approve & Send` trong Modal, modal đóng lại hoặc tự động chuyển sang ứng viên kế tiếp, dòng tương ứng trên Bảng lập tức chuyển trạng thái sang `APPROVED_QUEUED` hoặc `SENT`.

---

## 5. Phân tích Đánh đổi Kỹ thuật (Trade-off Analysis)

| Hướng tiếp cận | Ưu điểm | Nhược điểm / Rủi ro | Quyết định & Lý do |
| :--- | :--- | :--- | :--- |
| **Cách tiếp cận A: Chia đôi màn hình (Split-Pane Master-Detail)** | Danh sách và chi tiết nằm cùng 1 trang. | - Rất chật chội trên laptop 13-14 inch, cột danh sách chỉ thấy được mỗi handle.<br>- Ô soạn thảo bị hẹp ngang, khó đọc đoạn tweet dài. | ❌ **LOẠI BỎ** |
| **Cách tiếp cận B: Chuyển trang riêng biệt (`/candidates/[id]`)** | Rộng rãi tối đa. | - Rất tốn thao tác: Mỗi lần xem phải load trang mới, quay lại trang cũ bị mất vị trí cuộn chuột. | ❌ **LOẠI BỎ** |
| **Cách tiếp cận C (ĐƯỢC CHỌN): Table-First Workspace + Dedicated Review & Composer Modal** | - **Bảng dữ liệu toàn cảnh:** Hiển thị trọn vẹn Tên, Handle, Điểm số, Phân khúc, Địa điểm, Trạng thái.<br>- **Tìm kiếm & Lọc siêu tốc:** Thanh search kết hợp Filter pills phản hồi tức thì.<br>- **Không gian kiểm duyệt tập trung:** Modal mở ra rộng rãi với đầy đủ bằng chứng tô sáng và ô soạn tin nhắn to rõ ràng.<br>- **Thao tác nhanh:** Xóa ứng viên rác ngay tại bảng chỉ với 1 click `[🗑️]`. | Cần quản lý state đóng/mở modal và điều hướng hồ sơ tiếp theo. |  **CHỌN LỰA** (Tối ưu hóa năng suất vận hành thực tế cho VC team). |

---

## 6. Ràng buộc & Điều kiện bất biến (What Must Be True)
1. **Chốt chặn Phê duyệt:** Không có bất kỳ tin nhắn nào được gửi đi nếu người dùng chưa bấm nút **[Approve & Send]**.
2. **Bảo tồn nội dung chỉnh sửa:** Nếu người dùng sửa nội dung trong ô soạn thảo (`edited_dm`), khi gửi đi hệ thống bắt buộc gửi nội dung đã sửa, không gửi bản nháp cũ của AI.
3. **Phân định rõ Hành động bị chặn:** 
   - Ứng viên khóa DM (`can_dm = false` như `P019`): Nút [Approve & Send] bị khóa xám, hiển thị cảnh báo đỏ *"Người nhận khóa tin nhắn trên X"*.
   - Ứng viên hồ sơ rỗng (`INSUFFICIENT_EVIDENCE` như `P018`): Khóa nút gửi, hiển thị cảnh báo vàng *"Hồ sơ thiếu bằng chứng kỹ thuật"*.
   - Ứng viên bị lỗi chấm điểm (`AI_FAILED`): Hiển thị nút vàng `[🔄 Thử lại phân tích AI]`.

---

## 7. Khung dây Giao diện Chuẩn theo AppShell (Wireframes)

---

### Wireframe 1: Màn hình Bàn Duyệt Dạng Bảng (Candidate Table View)
Giao diện chính nằm trọn trong Canvas của AppShell, gồm Thanh tìm kiếm, Bộ lọc nhanh, và Bảng dữ liệu ứng viên:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ [X-Scout AI Logo] ◀│ 🎯 BÀN DUYỆT ỨNG VIÊN (REVIEW WORKSPACE)             [👤 General Partner ▾]│
├────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
│ 🧭 ĐIỀU HƯỚNG       │  ┌──────────────────────────────────────────────────────────────┬──────────┐  │
│                    │  │ Nhập tên, @handle, bio, từ khóa kỹ thuật...                 │ 🔍 TÌM   │  │
│ 📥 Nạp Ứng viên    │  └──────────────────────────────────────────────────────────────┴──────────┘  │
│                    │                                                                             │
│ 🎯 Bàn Duyệt HITL  │  [Tất cả (20)]  [🟢 Phù hợp Match (12)]  [⚪ Nhiễu Low Fit (4)]              │
│    [Đang chọn: 17] │  [🟡 Cần người xem (1)]  [🔴 Khóa DM (1)]  [🔵 Đã gửi (2)]                   │
│                    │                                                                             │
│ 📜 Sổ cái Gửi tin  │  ┌──────────────────┬─────────────────┬──────────┬──────────────┬───────────┐  │
│    [Needs: 2]      │  │ Ứng viên (Handle)│ Khu vực & Mảng  │ Điểm AI  │ Trạng thái   │ Hành động │  │
│                    │  ├──────────────────┼─────────────────┼──────────┼──────────────┼───────────┤  │
│ ⚖️ Đối chiếu AI    │  │ Minh Nguyen      │ Hanoi, VN       │ 🟢 4/4   │ PENDING      │ [👁️ Xem]  │  │
│                    │  │ @minh_quant      │ AI Infra        │ MATCH    │ REVIEW       │ [🗑️ Xóa] │  │
│                    │  ├──────────────────┼─────────────────┼──────────┼──────────────┼───────────┤  │
│ ⚙️ Sức khỏe Queue  │  │ Somchai Prasert  │ Bangkok, TH     │ 🟢 4/4   │ PENDING      │ [👁️ Xem]  │  │
│                    │  │ @dr_somchai_ai   │ Robotics        │ MATCH    │ REVIEW       │ [🗑️ Xóa] │  │
│                    │  ├──────────────────┼─────────────────┼──────────┼──────────────┼───────────┤  │
│                    │  │ Kevin Tan        │ Singapore       │ ⚪ 2/4   │ LOW FIT      │ [👁️ Xem]  │  │
│                    │  │ @kevin_wrapper   │ Apps/Wrapper    │ NO MATCH │ REVIEW       │ [🗑️ Xóa] │  │
│                    │  ├──────────────────┼─────────────────┼──────────┼──────────────┼───────────┤  │
│                    │  │ Arjun Rao        │ Singapore       │ 🟢 4/4   │ SEND_BLOCKED │ [👁️ Xem]  │  │
│                    │  │ @arjun_infer     │ Edge AI         │ MATCH    │ (DM Closed)  │ [🗑️ Xóa] │  │
│                    │  ├──────────────────┼─────────────────┼──────────┼──────────────┼───────────┤  │
│                    │  │ Ghost Builder    │ Stealth         │ 🟡 0/4   │ NEEDS HUMAN  │ [👁️ Xem]  │  │
│                    │  │ @ghost_builder   │ SEA Stealth     │ SPARSE   │ (No evidence)│ [🗑️ Xóa] │  │
│                    │  └──────────────────┴─────────────────┴──────────┴──────────────┴───────────┘  │
│                    │  Hiển thị 1 - 5 trên tổng số 20 ứng viên                      [◀ Trang 1 / 4 ▶]│
├────────────────────┤                                                                             │
│ [◀ Thu gọn Sidebar]│                                                                             │
└────────────────────┴─────────────────────────────────────────────────────────────────────────────┘
```

---

### Wireframe 2: Modal Kiểm duyệt & Soạn thảo Tin nhắn (Review & Composer Modal)
Khi người dùng bấm vào nút **`[👁️ Xem]`** trên bất kỳ dòng nào, Modal chuyên sâu bật lên:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│  KIỂM DUYỆT ỨNG VIÊN & SOẠN TIN NHẮN (Review & Composer)                                    [✕]  │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  👤 Minh Nguyen (@minh_quant) • Hanoi, Vietnam           Điểm AI: [ 🟢 4/4 HIGH FIT ]            │
│  Phân khúc: AI Infrastructure & Acceleration             Trạng thái DM: [ 🟢 Mở nhận tin nhắn ]  │
├──────────────────────────────────────────────────┬───────────────────────────────────────────────┤
│ 1. BẰNG CHỨNG & LÝ DO PHÙ HỢP (EVIDENCE)         │ 2. SOẠN THẢO DM CÁ NHÂN HÓA (COMPOSER)        │
│                                                  │                                               │
│ Tiểu sử X (Bio):                                 │ Bản nháp đề xuất bởi AI (Có thể gõ sửa):      │
│ "Co-founder @ TensorEdge VN. Building inference  │ ┌───────────────────────────────────────────┐ │
│  engine for telcos."                             │ │ Hi Minh — saw your recent post on        │ │
│                                                  │ │ AWQ-W4A8 speculative decoding for L40S    │ │
│ Lý do AI chấm phù hợp (Why they fit):            │ │ GPUs. We back deep-tech AI infra founders │ │
│ Founder có sản phẩm kỹ thuật sâu về suy luận LLM │ │ across SEA at X-Scout AI and would love   │ │
│ cho hạ tầng viễn thông, triển khai kernel thật.  │ │ to hear how adoption is going.            │ │
│                                                  │ │                                           │ │
│ Bài đăng gần nhất & Bằng chứng trích xuất:       │ │ P.S. Next week I'll be in Hanoi!          │ │
│ "...Benchmarking vLLM vs our custom kernel..."   │ └───────────────────────────────────────────┘ │
│                                                  │ Độ dài: 284 / 500 ký tự (Chuẩn mực)           │
│ Bằng chứng trích dẫn nguyên văn:                 │                                               │
│ ┌──────────────────────────────────────────────┐ │ Chế độ gửi: [⚡ Sandbox Mode (Giả lập)]     │
│ │ 💡 "...AWQ-W4A8 speculative decoding kernel │ │                                               │
│ │     for L40S GPUs (tensoredge-vn)..."        │ │ ┌─────────────┐ ┌───────────┐ ┌─────────────┐ │
│ └──────────────────────────────────────────────┘ │ │ 🔄 Tạo lại   │ │ 🗑️ Từ chối│ │ ⚡ PHÊ DUYỆT│ │
│                                                  │ │    bằng AI  │ │  (Reject) │ │  & GỬI DM   │ │
│                                                  │ └─────────────┘ └───────────┘ └─────────────┘ │
└──────────────────────────────────────────────────┴───────────────────────────────────────────────┘
```

---

## 8. Kịch bản Kiểm thử & Nghiệm thu (Acceptance Criteria)
- [ ] **Test Table Search & Filters:** Gõ từ khóa `"Robotics"` vào ô tìm kiếm $\rightarrow$ bảng lập tức lọc chỉ còn các ứng viên mảng Robotics. Bấm tab `"🟢 Phù hợp Match"` $\rightarrow$ chỉ hiện các ứng viên có điểm 3 hoặc 4.
- [ ] **Test Fast Delete from Table:** Bấm nút `[🗑️ Xóa]` tại dòng ứng viên `P009` (`@kevin_wrapper`) $\rightarrow$ chuyển trạng thái sang `REJECTED`, dòng ứng viên mờ đi hoặc biến mất khỏi danh sách chờ.
- [ ] **Test Modal Open & Evidence Display:** Bấm nút `[👁️ Xem]` tại hồ sơ `P002`, Modal mở lên hiển thị đúng đoạn trích dẫn màu hổ phách `"AWQ-W4A8 speculative decoding kernel"`.
- [ ] **Test Inline Edit in Modal:** Gõ thêm dòng *"P.S. Next week I'll be in Hanoi!"* vào ô soạn thảo, bấm [⚡ Phê duyệt & Gửi DM] $\rightarrow$ trong `outreach_ledger` lưu đúng nội dung đã chỉnh sửa.
- [ ] **Test Modal Action & Auto-refresh:** Sau khi bấm duyệt [⚡ PHÊ DUYỆT & GỬI DM] hoặc [🗑️ Từ chối (Reject)], modal tự động đóng lại, dòng ứng viên trong bảng lập tức cập nhật trạng thái mới (`QUEUED_FOR_SEND` hoặc `REJECTED`) và hiển thị thông báo toast thành công.
