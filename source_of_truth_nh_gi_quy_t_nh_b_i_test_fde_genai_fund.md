# SOURCE OF TRUTH & BẢN ĐÁNH GIÁ QUYẾT ĐỊNH
## Tuyển dụng: Forward Deployed Engineer (FDE) – GenAI Fund
**Bài toán:** X (Twitter) Autonomous Scouting & Personalized DM Outreach Tool for SEA AI/Robotics

---

## 1. TỔNG QUAN VÀ TIMELINE QUAN TRỌNG

| Hạng mục | Chi tiết | Ghi chú quan trọng |
| :--- | :--- | :--- |
| **Vị trí** | Forward Deployed Engineer (FDE) | Yêu cầu tư duy sản phẩm, tốc độ hiện thực hóa (execution), xử lý giới hạn thực tế (trade-offs). |
| **Công ty** | GenAI Fund | Quỹ đầu tư mạo hiểm tập trung vào Trí tuệ nhân tạo. |
| **Thời hạn xác nhận** | **Trước 12:00 trưa, Thứ Sáu 13/11/2026 (GMT+7)** | Phải gửi email xác nhận tham gia về `hr@genaifund.ai`. |
| **Thời hạn nộp bài** | **Trước 12:00 trưa, Thứ Ba 17/11/2026 (GMT+7)** | Tổng quỹ thời gian từ lúc xác nhận: **khoảng 96 giờ (~4 ngày)** bao gồm 2 ngày cuối tuần. |
| **Sản phẩm bàn giao** | 1. Working Prototype (URL hoặc Repo cài đặt < 15 phút)<br>2. Video demo (3–5 phút)<br>3. One-page write-up | Cả 3 cấu phần đều mang tính bắt buộc (Mandatory). |

---

## 2. MA TRẬN BÓC TÁCH YÊU CẦU KỸ THUẬT (SYSTEM DECONSTRUCTION)

Yêu cầu nhấn mạnh phương châm: **"Narrow & Reliable" (Hẹp nhưng cực kỳ ổn định và chạy mượt)** hơn là tính năng rộng nhưng nửa vời.

```
                      [Target Criteria / Seed Accounts]
                                      │
                                      ▼
                      ┌──────────────────────────────┐
                      │ 1. Scouting & Target Filter  │
                      │    - Match vs Target Persona │
                      │    - Reason for Fit (LLM)    │
                      └──────────────┬───────────────┘
                                      │
                                      ▼
                      ┌──────────────────────────────┐
                      │ 2. Deep Context Extractor    │
                      │    - Bio, Recent Posts, Work │
                      │    - Ground-truth Evidence   │
                      └──────────────┬───────────────┘
                                      │
                                      ▼
                      ┌──────────────────────────────┐
                      │ 3. Personalized Generator    │
                      │    - Anti-template DM        │
                      │    - SEA AI/Robotics Focus   │
                      └──────────────┬───────────────┘
                                      │
                                      ▼
                      ┌──────────────────────────────┐
                      │ 4. Human-In-The-Loop (HITL)  │
                      │    - Review / Edit / Reject  │
                      │    - Final User Sign-off     │
                      └──────────────┬───────────────┘
                                      │
                                      ▼
                      ┌──────────────────────────────┐
                      │ 5. State Machine & Dispatch  │
                      │    - De-duplication Engine   │
                      │    - Rate Limiter (X Policy) │
                      │    - Status Tracking CRM     │
                      └──────────────────────────────┘
```

### Chi tiết 5 module lõi:

| Module | Yêu cầu từ Đề bài | Thách thức kỹ thuật ngầm (Under-the-hood) |
| :--- | :--- | :--- |
| **1. Scouting & Discovery** | Tìm AI/Robotics founders/researchers tại ĐNÁ dựa trên hạt nhân (seeds) hoặc từ khóa. Có giải thích lý do fit. | Cào dữ liệu X bị cấm (`prohibited scraping`). API v2 của X rất hạn chế về tìm kiếm nếu dùng Free tier. Phải có giải pháp bypass hợp lệ hoặc dùng dataset/mock input thông minh. |
| **2. Context & Reason Generator** | Trích xuất profile, tweet gần nhất để làm dẫn chứng cá nhân hóa. Tránh văn mẫu. | Cần prompt engineering tốt với few-shot samples và cấu trúc trích xuất facts (JSON Schema) để tránh hallucination. |
| **3. Human-in-the-Loop UI** | Giao diện cho phép xem trước, sửa nội dung DM, bấm Approve mới được gửi. | Cần web frontend trực quan (Next.js/Streamlit/Tailwind) cho phép inline editing và thay đổi trạng thái theo thời gian thực. |
| **4. State Machine & De-dupe** | Tuyệt đối không gửi 2 lần cho 1 người; theo dõi pipeline: `Discovered` $\rightarrow$ `Drafted` $\rightarrow$ `Approved` $\rightarrow$ `Sent` $\rightarrow$ `Replied`. | Database (SQLite/Supabase/PostgreSQL) với unique constraint trên X User ID / Handle; cơ chế idempotency. |
| **5. Platform Compliance** | Tuân thủ giới hạn tần suất (Rate Limits) của X; bảo mật secrets; chi phí thấp. | Xử lý hàng đợi (Queue - e.g., BullMQ hoặc In-memory queue), token bucket / leaky bucket cho rate limiting. |

---

## 3. PHÂN TÍCH RỦI RO LỚN NHẤT: "BẪY X (TWITTER) API"

Đây là **điểm nghẽn chí mạng (Critical Bottleneck)** của bài test này mà ứng viên cần nhìn nhận rõ ràng:

1. **Rào cản chi phí X API:**
   * **Free Tier:** Hầu như chỉ hỗ trợ write cơ bản (tạo tweet), không đủ để search người dùng hoặc crawl lịch sử tweet.
   * **Basic Tier:** Tốn **$100/tháng**, giới hạn request rất chặt.
   * **Pro Tier:** Tốn **$5,000/tháng** (bất khả thi cho bài test tuyển dụng).
2. **Quy định "No Prohibited Scraping":**
   * Đề bài cấm cào dữ liệu trái phép (headless Puppeteer/Playwright không ủy quyền).
3. **Quy định "Không làm phiền người lạ" & "Bảo mật secrets":**
   * Không thể bắt ban giám khảo nhập khóa API $100 của họ, và bạn cũng không được public API keys của mình trong repo.
4. **Giải pháp kiến trúc hợp lệ (Architectural Compromise):**
   * Xây dựng **Dual-mode Engine**:
     * **Mode A (Live API/OAuth):** Kết nối qua X API chính thống với tài khoản test/whitelist.
     * **Mode B (Simulator / Sandbox Engine):** Cung cấp sẵn một bộ Seed Data thực tế (cache các profile AI/Robotics thật tại Singapore, Việt Nam, Indonesia) để ban giám khảo có thể bấm nút test ngay lập tức mà không cần bỏ $100 mua API X.
   * *Đây chính là tư duy FDE: Nhận diện điểm nghẽn hạ tầng và tạo ra cơ chế fallback thanh lịch (Graceful Fallback).*

---

## 4. MA TRẬN ĐÁNH GIÁ: CÓ NÊN THAM GIA KHÔNG? (GO / NO-GO)

### A. Đánh giá tính chất bài test
* **Là cơ hội tốt (Legitimate Test):**
  * Định nghĩa tiêu chí đánh giá rất rõ ràng: không yêu cầu UI màu mè, tập trung vào logic, rate limit, dedup, error handling và trade-off write-up.
  * Phản ánh đúng 100% công việc của một FDE: tiếp nhận bài toán nghiệp vụ chưa rõ ràng $\rightarrow$ làm chủ công nghệ $\rightarrow$ ra mắt prototype chạy được trong thời gian ngắn $\rightarrow$ giải thích trade-offs.
* **Rủi ro khai thác ý tưởng (Spec Work / Free Labor Risk):**
  * **Mức độ: Trung bình - Thấp.** Tool tìm kiếm founder/deal flow cho VC là bài toán phổ biến, đã có hàng trăm open-source repo tương tự. GenAI Fund không cần bạn code 4 ngày để lấy cắp một con bot gửi DM; họ đang kiểm tra **"System Thinking"** và **"Execution Speed"** của bạn.

---

### B. Bảng tự kiểm tra (Decision Checklist)

Hãy đánh dấu `[x]` vào các điều kiện dưới đây:

| STT | Câu hỏi tự đánh giá | Có | Không |
| :---: | :--- | :---: | :---: |
| 1 | Bạn có thể dành trọn vẹn **15 – 25 giờ** tập trung từ tối Thứ Sáu đến sáng Thứ Ba không? | [ ] | [ ] |
| 2 | Bạn đã quen thuộc với ít nhất một Full-stack framework nhanh (Next.js, FastAPI + React, hoặc Streamlit/Reflex)? | [ ] | [ ] |
| 3 | Bạn có kinh nghiệm tích hợp LLM APIs (OpenAI/Anthropic/Gemini) với JSON Schema / Structured Outputs? | [ ] | [ ] |
| 4 | Bạn biết cách giải quyết bài toán Rate Limit + De-duplication (Database schema, state machine)? | [ ] | [ ] |
| 5 | Bạn sẵn sàng quay video demo 5 phút bằng tiếng Anh/Việt trôi chảy và viết tài liệu 1 trang phân tích trade-offs? | [ ] | [ ] |

### QUY TẮC QUYẾT ĐỊNH:
* **NÊN THAM GIA (GO):** Nếu bạn trả lời **"CÓ" ít nhất 4/5 câu** (bắt buộc phải có câu 1 và 2). Bài test này là cơ hội hoàn hảo để bạn chứng minh năng lực vượt trội so với các ứng viên chỉ biết lý thuyết.
* **TỪ CHỐI / CÂN NHẮC LẠI (NO-GO):** Nếu bạn không thể thu xếp đủ thời gian cuối tuần này (dưới 10 giờ rảnh) HOẶC bạn không muốn làm việc với các bài test dạng take-home project chưa có cam kết phỏng vấn sâu.

---

## 5. BẢN ĐẶC TẢ PHẠM VI KHẢ THI TỐI THIỂU (MVP SCOPE SPECIFICATION)

Để hoàn thành trong 96 giờ với tiêu chí **"Narrow & Reliable"**, đây là phạm vi đề xuất cắt giảm thông minh:

### Trong phạm vi (IN-SCOPE - Phải làm xuất sắc):
1. **Targeting Seed Mode:**
   * Cho phép nhập 3-5 tài khoản hạt nhân (seed accounts) hoặc chọn phân khúc định sẵn: e.g., *"Robotics in Vietnam"*, *"LLM Researchers in Singapore"*.
   * Trả về danh sách ứng viên với cột: **"Why Relevant"** (giải thích ngắn gọn 2 câu lý do match).
2. **Context-Aware DM Drafter:**
   * Dùng Gemini 1.5 Flash hoặc GPT-4o-mini (chi phí gần bằng 0).
   * Prompt ràng buộc: Trích xuất ít nhất 1 chi tiết cụ thể từ bio/bài viết, giọng điệu founder-to-founder, có call-to-action (CTA) rõ ràng, dưới 280 ký tự.
3. **HITL Review Dashboard:**
   * Table/Card view: Xem Profile $\rightarrow$ Đọc DM đề xuất $\rightarrow$ Nút [Edit] [Approve] [Reject].
4. **State Machine & Database:**
   * SQLite / Supabase: Lưu trạng thái `NOT_CONTACTED`, `PENDING_REVIEW`, `APPROVED`, `SENT`, `REPLIED`.
   * Khóa cứng (Hard Constraint): Không bao giờ gửi 2 lần cho cùng một X handle.
5. **Deployment:**
   * Deploy miễn phí lên Vercel / Render / Railway trong 1 cú click.

### Ngoài phạm vi (OUT-OF-SCOPE - Cắt bỏ và giải thích trong write-up):
* *Không* làm hệ thống tự động cào hàng triệu tài khoản X (tốn chi phí, vi phạm platform).
* *Không* làm hệ sinh thái đa nền tảng (LinkedIn, Telegram...).
* *Không* làm auto-chat hội thoại đa vòng (chỉ tập trung vào First-Touch DM).

---

## 6. KẾ HOẠCH HÀNH ĐỘNG 96 GIỜ (EXECUTION PLAYBOOK)

```
[13/11 12:00] Gửi email xác nhận
      │
      ├─ Giai đoạn 1 (Thứ 6): Khung sườn & Data Model (Database, Mock API, Seed profiles)
      │
      ├─ Giai đoạn 2 (Thứ 7): Core LLM Engine & HITL Frontend (Drafter, Edit/Approve UI)
      │
      ├─ Giai đoạn 3 (Chủ Nhật): State Machine, Rate Limits & Deploy lên link thực tế
      │
      └─ Giai đoạn 4 (Thứ 2): Quay Video Demo (3-5m), Viết Write-up 1 trang, Clean Repo
      │
[17/11 12:00] Nộp bài hoàn tất
```

| Mốc thời gian | Nhiệm vụ cụ thể | Đầu ra cần đạt (Milestone Output) |
| :--- | :--- | :--- |
| **Thứ Sáu (13/11)**<br>*(Trước 12:00)* | Gửi email confirm tham gia cho HR. Thiết lập repo GitHub, setup schema Database (SQLite/Prisma). | Email sent; Repo skeleton sẵn sàng. |
| **Tối Thứ Sáu (13/11)** | Xây dựng pipeline dữ liệu mock + crawler/API X wrapper (Sandbox mode). | Chạy script lấy được 10 profile mẫu vào database. |
| **Thứ Bảy (14/11)** | Tích hợp LLM để phân tích "Match Reason" và tạo "Personalized DM". Xây dựng giao diện HITL (Review/Edit). | UI cho phép xem danh sách, chỉnh sửa DM trực tiếp trên web. |
| **Chủ Nhật (15/11)** | Hoàn thiện logic chống trùng (de-dupe), rate limit queue và mock/live sender. Deploy lên Vercel/Render. | Link web chạy trực tiếp, người ngoài vào dùng thử được ngay. |
| **Thứ Hai (16/11)** | Viết tài liệu `writeup.md` (1 trang: Trade-offs, Cost, AI verification). Quay video demo (Loom/OBS 3-5 phút). | Video sẵn sàng; Tài liệu hoàn tất; Repo có README cài < 15p. |
| **Thứ Ba (17/11)**<br>*(Trước 12:00)* | Kiểm tra lại toàn bộ link, quyền riêng tư video, gửi email nộp bài. | **Hoàn thành nộp bài.** |

---

## 7. MẪU EMAIL PHẢN HỒI XÁC NHẬN (CONFIRMATION TEMPLATE)

Nếu quyết định tham gia (**GO**), gửi email này trước **12:00 trưa Thứ Sáu 13/11/2026**:

```text
Tiêu đề: [Xác nhận tham gia] FDE Take-home Challenge - [Họ và Tên của bạn]
Gửi: hr@genaifund.ai

Kính gửi Ban Tuyển dụng GenAI Fund,

Tôi đã nhận được bản mô tả chi tiết cho bài tập thực tế vị trí Forward Deployed Engineer (FDE). 

Tôi viết email này để chính thức xác nhận sẽ tham gia hoàn thành bài tập theo đúng các tiêu chí và mốc thời gian đã đề ra. Tôi sẽ bàn giao đầy đủ 3 hạng mục (Working Prototype hosted/repo, Video demo và One-page write-up) trước 12:00 trưa Thứ Ba, ngày 17/11/2026 (GMT+7).

Để đảm bảo nguyên mẫu vận hành ổn định, an toàn và tuân thủ tuyệt đối quy định của nền tảng X mà không phát sinh chi phí hạ tầng bất hợp lý cho người đánh giá, giải pháp của tôi sẽ bao gồm cả chế độ Live Test (qua tài khoản ủy quyền) và Sandbox Demonstration Mode (với tập dữ liệu hạt nhân thực tế tại Đông Nam Á).

Rất mong được chia sẻ sản phẩm hoàn chỉnh cùng quý quỹ.

Trân trọng,
[Họ và tên của bạn]
[Số điện thoại]
[Link LinkedIn / GitHub]
```