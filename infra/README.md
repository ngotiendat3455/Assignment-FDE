# Docker Packaging & AWS Multi-Environment Infrastructure (`infra/`)

Tài liệu vận hành cho **Sub-task 7.3 (Docker & Docker Compose)** và **Sub-task 7.5 (Terraform Multi-Env AWS ECS Fargate + ALB + EFS/RDS)**.

---

## 1. Chiến lược 3 Môi trường ↔ 3 `RUNTIME_PROFILE`

Hệ thống ánh xạ **1-1** giữa 3 môi trường triển khai và 3 cấu hình của [`RuntimeGateway`](../backend/app/core/runtime_gateway.py):

| Môi trường | `RUNTIME_PROFILE` | Tài nguyên & Database | Chính sách AI & X API | Mục đích & Lưu ý Vận hành |
| :--- | :--- | :--- | :--- | :--- |
| **`dev`** | `OFFLINE_MOCK` | • `db`: SQLite WAL trên **Amazon EFS** (`desired=1`)<br>• `compute`: Fargate Spot `0.25vCPU/512MB`<br>• Chạy kèm container nội bộ `x-simulator:8099` | • **AI:** Khóa cứng `$0` `DETERMINISTIC_RUBRIC` (0 gọi mạng ngoài).<br>• **X Lookup:** Gọi `x-simulator.<env>.local:8099/2`.<br>• **DM:** `SANDBOX` cứng (0 DM thật). | Demo UI, phát triển tính năng, chạy QA tự động không tốn $1 API nào. |
| **`staging`** | `HYBRID_AUTO` | • `db`: SQLite WAL trên **Amazon EFS** (`desired=1`)<br>• `compute`: Fargate `0.5vCPU/1GB` (BE) + `0.25vCPU/512MB` (FE)<br>• Chạy kèm `x-simulator` dự phòng | • **AI:** Gọi Live Gemini/OpenAI nếu Secret có key thật; chưa điền key vẫn chạy `$0` để không sập môi trường demo.<br>• **X Lookup:** Dùng Live X nếu có Bearer token thật, else simulator.<br>• **DM:** `SANDBOX` mặc định (bật `LIVE_X_DRY_RUN=true` + `ALLOWED_TEST_HANDLES` khi test dry-run). | Tiền kiểm tích hợp & đo Calibration Alignment thật.<br>**Lưu ý quan trọng:** Trước khi cắt sang `prod`, nên test smoke 1 lượt với `RUNTIME_PROFILE=LIVE_PRODUCTION` trên staging hoặc kiểm tra `GET /api/system/runtime` (`live_production_readiness.ready == true`) để chắc chắn không có silent fallback do thiếu key. |
| **`prod`** | `LIVE_PRODUCTION` | • `db`: **Amazon RDS PostgreSQL 16** (Multi-AZ, encrypted, backups)<br>• `compute`: Multi-task Fargate (`desired >= 2`, AutoScaling CPU 70%) | • **AI:** Bắt buộc Live Gemini/OpenAI; **cấm silent fallback** (thiếu/lỗi đẩy sang `AI_FAILED`).<br>• **X Lookup:** Bắt buộc `https://api.twitter.com/2` + `X_BEARER_TOKEN` thật.<br>• **DM:** `LIVE_X` + `LIVE_X_DRY_RUN=false` + bắt buộc 4 OAuth 1.0a keys + `ALLOWED_TEST_HANDLES` guard. | Vận hành chính thức. Bảo đảm dữ liệu thật 100%, không bao giờ sinh điểm `$0` hay `sim_dm_...` giả. |

---

## 2. Chạy Cục bộ với Docker Compose (Sub-task 7.3)

### Cách A — Chế độ tiêu chuẩn (`:3000` Frontend + `:8000` Backend + internal `x-simulator`)

```powershell
# 1. Tạo file env cho Docker (mặc định RUNTIME_PROFILE=OFFLINE_MOCK)
Copy-Item .env.docker.example .env.docker

# 2. Build & khởi động nền
docker compose --env-file .env.docker up --build -d

# 3. Kiểm tra trạng thái healthy của tất cả containers
docker compose ps
```

Mở trình duyệt: **`http://localhost:3000/login`**
Kiểm tra `RuntimeGateway`: **`http://localhost:8000/api/system/runtime`**

### Cách B — Chế độ Same-Origin giống hệt AWS ALB qua Nginx (`http://localhost:80`)

```powershell
docker compose --env-file .env.docker --profile prod-sim up --build -d
```

Nginx (cổng `80`, cấu hình tại [`infra/nginx/nginx.conf`](nginx/nginx.conf)) định tuyến đồng nhất cùng domain:
- `/api/auth/*` $\rightarrow$ `frontend:3000` *(giữ Next.js BFF `Set-Cookie: HttpOnly`)*
- `/api/*` $\rightarrow$ `backend:8000` *(FastAPI REST)*
- `/*` $\rightarrow$ `frontend:3000` *(Next.js UI)*

Nhờ [`frontend/src/lib/api-config.ts`](../frontend/src/lib/api-config.ts) (`NEXT_PUBLIC_API_BASE_URL=auto`), cùng một Docker image `frontend` tự động gọi `/api` (Zero CORS) khi chạy qua `:80` Nginx hoặc HTTPS AWS ALB, và gọi `http://localhost:8000/api` khi chạy trực tiếp trên `:3000`.

### Kiểm chứng Bền vững Dữ liệu (`MQ-F2`)

```powershell
# Sau khi nạp Starter Pack và gửi DM ở localhost:3000:
docker compose restart backend
# Tải lại trình duyệt: dữ liệu SQLite tại named volume genai_sqlite_data (/app/data/outreach.db) vẫn còn nguyên 100%.
```

---

## 3. Triển khai AWS bằng Terraform (Sub-task 7.5)

Cấu trúc mã nguồn Hạ tầng tại [`infra/terraform/`](terraform/):
- [`versions.tf`](terraform/versions.tf), [`main.tf`](terraform/main.tf), [`variables.tf`](terraform/variables.tf), [`outputs.tf`](terraform/outputs.tf)
- Modules: `network/`, `alb/`, `storage_secrets/`, `ecs_cluster/`
- Biến môi trường tách riêng: [`dev.tfvars`](terraform/environments/dev.tfvars), [`staging.tfvars`](terraform/environments/staging.tfvars), [`prod.tfvars`](terraform/environments/prod.tfvars)

```bash
cd infra/terraform

# 1. Khởi tạo Terraform (dùng backend.tf.example để cấu hình S3 State + DynamoDB Lock cho mỗi env)
terraform init

# 2. Kiểm tra plan cho từng môi trường tương ứng
terraform plan -var-file="environments/dev.tfvars"
terraform plan -var-file="environments/staging.tfvars"
terraform plan -var-file="environments/prod.tfvars"

# 3. Áp dụng triển khai (ví dụ dev)
terraform apply -var-file="environments/dev.tfvars"

# 4. Nạp các key bí mật cho staging/prod vào AWS Secrets Manager (KHÔNG lưu key trong tfvars):
aws secretsmanager put-secret-value \
  --secret-id staging/genai-fde/app-secrets \
  --secret-string '{"SECRET_KEY":"<random-jwt>","GEMINI_API_KEY":"<key>","OPENAI_API_KEY":"","X_BEARER_TOKEN":"<bearer>","X_API_KEY":"","X_API_SECRET":"","X_ACCESS_TOKEN":"","X_ACCESS_TOKEN_SECRET":""}'
```

