# Feature Spec 03: Authentication, Security Hygiene & Demo Login
*(WBS Task 3 / Platform Security)*

---

## 1. Design Thinking: Thấu cảm, Định nghĩa & Ý tưởng hóa (Empathize, Define, Ideate)

### A. Empathize (Thấu cảm người dùng)
1. **VC Investment Team (Người dùng thật):**
   - Cần phân quyền và định danh rõ ràng: ai là người duyệt hồ sơ (`reviewed_by`), ai là người bấm gửi DM (`sent_by`) để giữ trách nhiệm giải trình nội bộ.
   - Không muốn các API nhạy cảm (danh sách founder, draft DM, outreach history) bị lộ ra ngoài Internet.
2. **Hiring Committee / Giám khảo:**
   - *Áp lực thời gian:* Chỉ có < 15 phút để test toàn bộ ứng dụng trên máy mới.
   - *Sự ức chế lớn nhất:* Ứng dụng bắt phải cấu hình Google Cloud OAuth Client ID, Redirect URI, hoặc bắt buộc phải gõ form đăng ký tài khoản dài dòng mới vào được dashboard.

### B. Define (Định nghĩa bài toán & HMW)
- **Tuyên ngôn vấn đề (POV):**
  > *"Hệ thống cần cơ chế xác thực bảo mật chuẩn công nghiệp để phân quyền và bảo vệ dữ liệu nhạy cảm, đồng thời phải cung cấp trải nghiệm đăng nhập 1-click hoàn toàn 0-ma sát cho ban giám khảo để kiểm thử tức thì trong 1 giây."*
- **3 Câu hỏi cốt lõi (How Might We):**
  - **HMW-1 (Zero Friction for Reviewer):** Làm thế nào để người chấm bài vào ngay Dashboard với tư cách GenAI Fund Partner chỉ bằng 1 cú click chuột?
  - **HMW-2 (Bulletproof API Security):** Làm thế nào để đảm bảo không một ai có thể xem dữ liệu hay gửi DM trái phép mà không có token JWT hợp lệ?
  - **HMW-3 (Secret Hygiene):** Làm thế nào để các API key (Gemini, X Token) tuyệt đối không bao giờ rò rỉ ra trình duyệt phía client?

### C. Ideate (Ý tưởng hóa giải pháp)
1. **Nút "1-Click Partner Demo Login" trên màn hình Đăng nhập:**
   - Cung cấp sẵn nút đăng nhập nhanh với tài khoản đối tác được tự động seed sẵn trong Database: `partner@genaifund.ai`.
2. **Cơ chế JWT Bearer Auth chuẩn Stateless:**
   - Cấp access token thời hạn an toàn, mã hóa mật khẩu bằng `bcrypt`.
3. **Chốt chặn Middleware FastAPI Dependency:**
   - Tiêm dependency `get_current_user` vào toàn bộ router nghiệp vụ (`/api/candidates`, `/api/outreach`, `/api/dashboard`).

---

## 2. Mục tiêu cốt lõi (Core Purpose)
Cung cấp giải pháp xác thực (Authentication) bảo mật cao, bảo vệ toàn bộ API nghiệp vụ và dữ liệu nhạy cảm của quỹ, đồng thời cung cấp trải nghiệm đăng nhập tức thì cho người đánh giá thông qua tài khoản đối tác mẫu được cài đặt sẵn.

---

## 3. Yêu cầu từ Đề bài (Requirements from Prompt)
- Tuyệt đối không chia sẻ thông tin đăng nhập cá nhân hoặc nhúng secrets vào mã nguồn công khai.
- Đội ngũ quỹ có thể tự sử dụng mà không cần lập trình viên ngồi cạnh.
- Đảm bảo tính bảo mật và kiểm soát truy cập cho công cụ gửi tin nhắn.

---

## 4. Thách thức Kỹ thuật ngầm (Under-the-hood Technical Challenges)
- **Rào cản Cấu hình OAuth Ngoài:** Nếu dùng Google OAuth hoặc Auth0, người chấm bắt buộc phải tạo app trên Google Cloud Console, tạo redirect URIs $\rightarrow$ vi phạm tiêu chí *"run under 15 minutes"*.
- **Rủi ro của "No Auth":** Nếu bỏ qua hoàn toàn phần đăng nhập, sản phẩm sẽ bị đánh giá là đồ án sơ sài, thiếu tính năng phân quyền và không lưu được người thực hiện hành động gửi tin (`sent_by_user_id`).
- **Rò rỉ Khóa Bí mật:** LLM API Key hoặc X Bearer Token nếu bị vô tình serialize ra JSON response sẽ bị đánh dấu **Fail Bảo Mật**.

---

## 5. Phân tích Đánh đổi Kỹ thuật (Trade-off Analysis)

| Hướng tiếp cận | Ưu điểm | Nhược điểm / Rủi ro | Quyết định & Lý do |
| :--- | :--- | :--- | :--- |
| **Cách tiếp cận A: OAuth2 Google / Auth0** | Chuẩn SSO doanh nghiệp. | Bắt buộc cấu hình cloud credentials phức tạp, tốn > 30 phút. | ❌ **LOẠI BỎ** |
| **Cách tiếp cận B: Hoàn toàn không có Đăng nhập (No Auth)** | Không tốn thời gian login. | Bị gắn cờ **Red Flag**: Không bảo vệ API, không thể lưu vết trách nhiệm. | ❌ **LOẠI BỎ** |
| **Cách tiếp cận C (ĐƯỢC CHỌN): Native JWT Auth + Seeded Partner User + 1-Click Demo Login** | - **Bảo mật tuyệt đối:** Mã hóa bcrypt, JWT Bearer Token, middleware bảo vệ 100% API.<br>- **Zero Friction:** Có nút **"1-Click Demo Login"** đăng nhập thẳng trong 1 giây.<br>- **Không phụ thuộc Cloud ngoài:** Chạy offline hoàn toàn trên SQLite. | Cần viết thêm 3 endpoint xác thực cơ bản. |  **CHỌN LỰA** (Cân bằng xuất sắc giữa Security và Turnkey UX). |

---

## 6. Ràng buộc & Điều kiện bất biến (What Must Be True)
1. **Bảo vệ API Nghiệp vụ:** Mọi request tới `/api/candidates/*`, `/api/outreach/*`, `/api/dashboard/*` nếu không có Bearer token hợp lệ đều nhận mã lỗi `401 Unauthorized`.
2. **Không Rò rỉ Bí mật (Secret Hygiene):** Khóa bí mật (`GEMINI_API_KEY`, `X_BEARER_TOKEN`) chỉ được đọc từ biến môi trường máy chủ, tuyệt đối không xuất hiện trong bất kỳ response JSON nào gửi về trình duyệt.
3. **Mã hóa Mật khẩu Chuẩn:** Toàn bộ mật khẩu lưu trong bảng `users` bắt buộc phải được băm bằng thuật toán `bcrypt` có muối ngẫu nhiên (salt).

---

## 7. Đặc tả Kỹ thuật chi tiết (Technical Specification)

### API Endpoints Xác thực:
- `POST /api/auth/register`: Đăng ký tài khoản nội bộ mới (email, password, full_name, role).
- `POST /api/auth/login`: Nhận `username` (email) và `password`, trả về JWT token:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "email": "partner@genaifund.ai",
      "full_name": "General Partner",
      "role": "partner"
    }
  }
  ```
- `GET /api/auth/me`: Xác thực token và trả về profile người dùng hiện tại.

### Seeded Partner Credentials:
- **Email:** `partner@genaifund.ai`
- **Mật khẩu:** `GenAIFund2026!`
- **Role:** `partner`

### FastAPI Security Implementation (`backend/app/core/security.py`):
```python
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```

---

## 8. Kịch bản Kiểm thử & Nghiệm thu (Acceptance Criteria)
- [ ] **Test Unauthenticated Rejection:** Gọi `GET /api/candidates` mà không truyền Header `Authorization` $\rightarrow$ nhận mã `401 Unauthorized`.
- [ ] **Test 1-Click Login:** Mở màn hình Login, bấm nút *"⚡ 1-Click Demo Login as Partner"* $\rightarrow$ hệ thống gửi request đăng nhập tự động, lưu token vào `localStorage`, và chuyển hướng vào Review Workspace.
- [ ] **Test Wrong Password:** Thử đăng nhập với mật khẩu sai $\rightarrow$ nhận mã `401 Incorrect email or password`.

