# GenAI Fund – Autonomous Scouting & Personalized Outreach System

Hệ thống tìm kiếm, chấm điểm AI (**Tri-Guard**), cá nhân hóa **DM X/Twitter** có **Human-in-the-Loop (HITL)** và **Outreach Ledger** chống gửi trùng lặp, điều phối tập trung qua **3 `RUNTIME_PROFILE`** trên cùng một codebase cho **Local Dev**, **Docker Compose**, và **AWS ECS Fargate (Terraform)**.

> Tài liệu chi tiết:
> - Kế hoạch & Kiểm chứng bàn giao: [`context/features/07-verification-and-handover.md`](context/features/07-verification-and-handover.md)
> - Runbook Hạ tầng Docker & Terraform chi tiết: [`infra/README.md`](infra/README.md)
> - Checklist Manual QA: [`tests/manual/MANUAL_QA_CHECKLIST.md`](tests/manual/MANUAL_QA_CHECKLIST.md)

---

## 1. Kiến trúc & Ánh xạ 3 `RUNTIME_PROFILE` (`RuntimeGateway`)

Hệ thống gồm **Backend (`FastAPI` + SQLite WAL / PostgreSQL)** và **Frontend (`Next.js 15 App Router` + BFF `HttpOnly` Cookie)**. Mọi quyết định gọi **AI (Gemini/OpenAI vs `$0` Rubric)** và **X API v2 (Real vs Simulator / Sandbox)** đều đi qua **1 cổng duy nhất** [`backend/app/core/runtime_gateway.py`](backend/app/core/runtime_gateway.py):

| `RUNTIME_PROFILE` | Bản chất vận hành | 1. AI Chấm điểm & Soạn DM | 2. Tra cứu X (`x-lookup`) | 3. Gửi DM (`/send`) | Ánh xạ môi trường chuẩn |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`OFFLINE_MOCK`** | **`$0` Khóa cứng nội bộ** *(mặc định Dev & QA)* | Khóa `DETERMINISTIC_RUBRIC` (`tri-guard-local-v1`), **0 gọi mạng ngoài** kể cả khi máy có lưu `GEMINI_API_KEY`. | Tự động trỏ **X Simulator** (`127.0.0.1:8099` khi chạy local, `x-simulator:8099` trong Docker/ECS) + token `sim_dev_bearer_token`. | Khóa `SANDBOX` / `LIVE_X_DRY_RUN` (sinh `sim_dm_...`, không bao giờ gọi OAuth 1.0a ra ngoài). | • **Local Dev / E2E**<br>• **Docker mặc định**<br>• **AWS `dev`** |
| **`HYBRID_AUTO`** | **Linh hoạt từng phần** *(tiền kiểm Pre-Prod)* | Có `GEMINI_API_KEY` / `OPENAI_API_KEY` thật $\rightarrow$ gọi Live LLM; để trống $\rightarrow$ fallback `$0` Rubric. | Tự động chạy theo `X_API_BASE_URL` & `X_BEARER_TOKEN` đang cấu hình trong env. | Chạy theo `DISPATCH_MODE` (`SANDBOX` mặc định, hoặc `LIVE_X` + `LIVE_X_DRY_RUN=True` khi test whitelist). | • **Local test lẻ từng key**<br>• **Docker staging-sim**<br>• **AWS `staging`** |
| **`LIVE_PRODUCTION`** | **Strict Live — Cấm fallback ngầm** | Bắt buộc Live Gemini/OpenAI. Thiếu key hoặc lỗi mạng $\rightarrow$ đẩy ứng viên vào **`AI_FAILED`** (không bao giờ fallback về điểm `$0`). | Bắt buộc `https://api.twitter.com/2` + `X_BEARER_TOKEN` thật (trỏ localhost/simulator hoặc dùng `sim_*` $\rightarrow$ chặn **`HTTP 503`**). | Khi `DISPATCH_MODE=LIVE_X`: kiểm tra **`ALLOWED_TEST_HANDLES`** + bắt buộc đủ **4 khóa OAuth 1.0a** + `LIVE_X_DRY_RUN=False` (thiếu $\rightarrow$ **`HTTP 503`**, cấm tạo `sim_dm_...` giả). | • **Local nghiệm thu Live**<br>• **Docker `--profile prod-sim`**<br>• **AWS `prod`** |

**Giám sát nguồn gốc thực thi:**
- Mọi response từ `/api/queue/evaluate/{id}`, `/api/queue/process`, `/api/ingestion/x-lookup`, `/api/candidates/{id}/send` đều đính kèm **`execution_meta`** (`profile`, `ai_engine` / `source_mode` / `dispatch_execution`, `external_network_call`).
- Kiểm tra nhanh trạng thái tập trung qua **`GET /api/system/runtime`** (xem thêm `live_production_readiness.ready` & `missing_requirements`) hoặc `/api/health`.

---

## 2. Cách chạy Local Trực tiếp (Không Docker)

### 2.1. Cài đặt Dependencies (Chạy 1 lần đầu)

Tại thư mục gốc `d:\AssignmentFDE`:

```powershell
# 1. Backend (Python 3.10+)
pip install -r backend/requirements.txt

# 2. Frontend (Node.js 20+)
cd frontend
npm.cmd install
cd ..

# 3. Tạo file cấu hình Backend (nếu chưa có)
Copy-Item backend/.env.example backend/.env
```

> **Lưu ý quan trọng:** FastAPI đọc `backend/.env` lúc khởi động (`uvicorn --reload` chỉ watch file `.py`, **không** tự nạp lại `.env`). Sau khi sửa `backend/.env`, luôn `Ctrl+C` và bật lại `uvicorn`.

### 2.2. Cấu hình `backend/.env` cho từng `RUNTIME_PROFILE`

Mở `backend/.env` và chọn **1 trong 3 cấu hình**:

<details>
<summary><strong>A. Chạy Local với <code>RUNTIME_PROFILE=OFFLINE_MOCK</code> ($0 Dev & QA, không cần key)</strong></summary>

```dotenv
RUNTIME_PROFILE=OFFLINE_MOCK
DISPATCH_MODE=SANDBOX
X_SIMULATOR_BASE_URL=http://127.0.0.1:8099/2
# GEMINI_API_KEY / OPENAI_API_KEY / X_BEARER_TOKEN để trống (RuntimeGateway tự bỏ qua)
```

</details>

<details>
<summary><strong>B. Chạy Local với <code>RUNTIME_PROFILE=HYBRID_AUTO</code> (Ví dụ: Bật Live AI trước, giữ X Simulator/Sandbox)</strong></summary>

```dotenv
RUNTIME_PROFILE=HYBRID_AUTO

# 1. Bật Live AI thật (chọn Gemini hoặc OpenAI; bỏ trống nếu muốn test $0 Rubric)
GEMINI_API_KEY=<key_gemini_cua_ban>
# OPENAI_API_KEY=<key_openai_cua_ban>

# 2. X Lookup: dùng Simulator (:8099) hoặc X API thật
X_API_BASE_URL=http://127.0.0.1:8099/2
X_BEARER_TOKEN=sim_dev_bearer_token

# 3. DM Dispatch: giữ SANDBOX (hoặc LIVE_X + LIVE_X_DRY_RUN=True để test an toàn)
DISPATCH_MODE=SANDBOX
LIVE_X_DRY_RUN=True
ALLOWED_TEST_HANDLES=linhtran_robo,minh_quant,test_builder_sea
```

</details>

<details>
<summary><strong>C. Chạy Local với <code>RUNTIME_PROFILE=LIVE_PRODUCTION</code> (Nghiệm thu 100% Live API, cấm fallback)</strong></summary>

```dotenv
RUNTIME_PROFILE=LIVE_PRODUCTION

# 1. Bắt buộc Live LLM
GEMINI_API_KEY=<key_gemini_cua_ban>

# 2. Bắt buộc Live X API v2
X_API_BASE_URL=https://api.twitter.com/2
X_BEARER_TOKEN=<x_bearer_token_that>

# 3. Gửi DM: dùng SANDBOX nếu chưa muốn gửi thật, hoặc bật LIVE_X kèm đủ 4 khóa OAuth 1.0a
DISPATCH_MODE=LIVE_X
LIVE_X_DRY_RUN=False
ALLOWED_TEST_HANDLES=<handle_test_cho_phep>
X_API_KEY=<x_api_key>
X_API_SECRET=<x_api_secret>
X_ACCESS_TOKEN=<x_access_token>
X_ACCESS_TOKEN_SECRET=<x_access_token_secret>
```

</details>

### 2.3. Khởi động các Terminal Local

```powershell
# Terminal 0 (Bật khi dùng OFFLINE_MOCK hoặc HYBRID_AUTO trỏ simulator :8099):
# Lưu ý: x_simulator.py tự chạy uvicorn bên trong nên KHÔNG gõ chữ `uvicorn` ở Cách 1
python -m backend.scripts.x_simulator --host 127.0.0.1 --port 8099
# (Hoặc: python -m uvicorn backend.scripts.x_simulator:simulator_app --host 127.0.0.1 --port 8099)

# Terminal 1 — Backend FastAPI (:8000):
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend Next.js (:3000):
cd frontend; npm.cmd run dev
```

- Web UI: **`http://localhost:3000/login`**
  - **Partner (Full quyền):** `partner@genaifund.ai` / `GenAIFund2026!`
  - **Analyst (Nếu reset kèm `--with-analyst`, để test `/403`):** `analyst@genaifund.ai` / `Analyst2026!`
- Kiểm tra profile đang chạy: **`http://127.0.0.1:8000/api/system/runtime`**
- Kiểm tra X Simulator `:8099` đang sống: **`http://127.0.0.1:8099/health`** *(hỗ trợ các handle giả lập lỗi `@sim_401`, `@credits_depleted`, `@forbidden_handle`, `@missing_user`, `@rate_limit`)*.

---

## 3. Cách chạy Local bằng Đóng gói Docker Image & Docker Compose theo từng `RUNTIME_PROFILE`

Hệ thống dùng [`docker-compose.yml`](docker-compose.yml) gồm các container:
- `x-simulator` (nội bộ cổng `8099`, chạy từ [`backend/Dockerfile`](backend/Dockerfile))
- `backend` (cổng `8000`, gắn named volume **`genai_sqlite_data:/app/data`** lưu `outreach.db` bền vững qua restart)
- `frontend` (cổng `3000`, multi-stage build **`output: "standalone"`** từ [`frontend/Dockerfile`](frontend/Dockerfile) với `NEXT_PUBLIC_API_BASE_URL=auto`)
- `proxy` (tùy chọn `--profile prod-sim`, Nginx [`infra/nginx/nginx.conf`](infra/nginx/nginx.conf) ở cổng **`80`** giả lập y hệt rule định tuyến của AWS ALB: `/api/auth/* -> frontend`, `/api/* -> backend`, `/* -> frontend`).

### Bước 1: Tạo `.env.docker` từ file mẫu

```powershell
Copy-Item .env.docker.example .env.docker
```

*(Nhớ giữ Docker Desktop ở trạng thái Running trước khi chạy `docker build` / `docker compose`.)*

### Bước 2: Chỉnh `.env.docker` & Chạy cho từng `RUNTIME_PROFILE`

#### Profile 1: `RUNTIME_PROFILE=OFFLINE_MOCK` (Mặc định `$0`, không cần key)

File `.env.docker` mặc định đã đặt sẵn cho chế độ này:
```dotenv
RUNTIME_PROFILE=OFFLINE_MOCK
DISPATCH_MODE=SANDBOX
X_SIMULATOR_BASE_URL=http://x-simulator:8099/2
```
Khởi chạy 2 cổng tiêu chuẩn (`:3000` / `:8000`):
```powershell
docker compose --env-file .env.docker up --build -d
# Mở: http://localhost:3000/login
```

#### Profile 2: `RUNTIME_PROFILE=HYBRID_AUTO` (Test Live Gemini + Simulator / Dry-run trong Docker)

Sửa trong `.env.docker`:
```dotenv
RUNTIME_PROFILE=HYBRID_AUTO
GEMINI_API_KEY=<key_gemini_that>

# Nếu chưa có X Bearer thật, trỏ vào tên DNS nội bộ của container x-simulator:
X_API_BASE_URL=http://x-simulator:8099/2
X_BEARER_TOKEN=sim_dev_bearer_token

# Giữ an toàn khi test pre-prod:
DISPATCH_MODE=SANDBOX
# Hoặc thử nhánh LIVE_X nhưng chỉ dry-run trong whitelist:
# DISPATCH_MODE=LIVE_X
# LIVE_X_DRY_RUN=True
# ALLOWED_TEST_HANDLES=linhtran_robo,minh_quant,test_builder_sea
```
Chạy lại container để nạp env mới:
```powershell
docker compose --env-file .env.docker up --build -d
```

#### Profile 3: `RUNTIME_PROFILE=LIVE_PRODUCTION` (Mô phỏng Production Strict + Nginx ALB tại `:80`)

Sửa trong `.env.docker`:
```dotenv
RUNTIME_PROFILE=LIVE_PRODUCTION
SECRET_KEY=<chuoi-bi-mat-dai-ngau-nhien>

GEMINI_API_KEY=<key_gemini_that>
X_API_BASE_URL=https://api.twitter.com/2
X_BEARER_TOKEN=<x_bearer_token_that>

# Muốn bắn DM thật phải đặt LIVE_X_DRY_RUN=False và đủ 4 khóa OAuth + whitelist:
DISPATCH_MODE=LIVE_X
LIVE_X_DRY_RUN=False
ALLOWED_TEST_HANDLES=<handle_test_trong_whitelist>
X_API_KEY=<x_api_key>
X_API_SECRET=<x_api_secret>
X_ACCESS_TOKEN=<x_access_token>
X_ACCESS_TOKEN_SECRET=<x_access_token_secret>
```
Chạy kèm Nginx reverse proxy `--profile prod-sim` (Zero CORS qua cùng domain `http://localhost`):
```powershell
docker compose --env-file .env.docker --profile prod-sim up --build -d
# Mở: http://localhost/login
# Kiểm tra RuntimeGateway Readiness: http://localhost/api/system/runtime
```

> **Cơ chế 1 image cho mọi cổng/domain:** Nhờ [`frontend/src/lib/api-config.ts`](frontend/src/lib/api-config.ts) (`NEXT_PUBLIC_API_BASE_URL=auto`), **cùng một Docker image `frontend`** tự gọi `http://localhost:8000/api` khi bạn mở `:3000`, và tự động đổi sang `/api` (Same-Origin) khi bạn mở qua Nginx `:80` hoặc AWS ALB.

### Bước 3: Lệnh Build Image riêng lẻ & Kiểm chứng Persistence (`MQ-F2`)

```powershell
# Build từng Docker image độc lập (dùng cho ECR / CI)
docker build -f backend/Dockerfile -t genai-fde-backend:local .
docker build -f frontend/Dockerfile --build-arg NEXT_PUBLIC_API_BASE_URL=auto -t genai-fde-frontend:local ./frontend

# Kiểm tra tất cả container đạt trạng thái (healthy)
docker compose ps

# Kiểm chứng RuntimeGateway profile đang chạy
curl.exe http://localhost:8000/api/system/runtime

# Test bền vững dữ liệu SQLite (/app/data/outreach.db) sau khi nạp Starter Pack & gửi DM:
docker compose restart backend

# Dừng container (giữ lại DB volume):
docker compose --profile prod-sim down
# Dừng và XÓA SẠCH hoàn toàn volume SQLite cũ để tạo bản build sạch chỉ có 1 User đăng nhập:
docker compose --env-file .env.docker --profile prod-sim down -v && docker compose --env-file .env.docker up --build -d
```

> **Lưu ý về dữ liệu khởi tạo sạch:** Mặc định `AUTO_SEED_LEDGER_BASELINE=False` (trong `.env.docker` và `backend/.env.example`) nên khi dựng container mới (hoặc sau `reset_clean_users.py --yes`), DB **chỉ giữ duy nhất 1 User đăng nhập** (`partner@genaifund.ai`) và `0` candidates / `0` ledger, không còn tự động bơm 4 bản ghi lịch sử `OUT-101..104` lúc vừa mở web. Nếu dựng lại Docker sau khi đã từng test trước đó, hãy chạy `down -v` để xóa named volume `genai_sqlite_data` cũ.

---

## 4. Cách dùng & Triển khai AWS (Terraform + ECS Fargate) theo từng `RUNTIME_PROFILE`

Toàn bộ mã nguồn IaC đặt tại [`infra/terraform/`](infra/terraform/) (modules: `network/`, `alb/`, `storage_secrets/`, `ecs_cluster/`) và CI/CD blueprint tại [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml).

### 4.1. Ánh xạ 3 Môi trường AWS (`environments/{dev,staging,prod}.tfvars`)

| Thông số Hạ tầng & Bảo mật | `dev` ([`dev.tfvars`](infra/terraform/environments/dev.tfvars)) | `staging` ([`staging.tfvars`](infra/terraform/environments/staging.tfvars)) | `prod` ([`prod.tfvars`](infra/terraform/environments/prod.tfvars)) |
| :--- | :--- | :--- | :--- |
| **`runtime_profile`** | **`OFFLINE_MOCK`** | **`HYBRID_AUTO`** | **`LIVE_PRODUCTION`** |
| **Domain mặc định** | `dev.scout.genaifund.ai` | `staging.scout.genaifund.ai` | `scout.genaifund.ai` *(bắt buộc điền `acm_certificate_arn` cho HTTPS :443)* |
| **ECS Fargate Sizing** | FE `0.25 vCPU / 512MB` (Spot)<br>BE `0.25 vCPU / 512MB` (`1` task) | FE `0.25 vCPU / 512MB`<br>BE `0.5 vCPU / 1GB` (`1` task) | FE `0.5 vCPU / 1GB` (`2` tasks)<br>BE `1 vCPU / 2GB` (`2` tasks + CPU AutoScaling) |
| **Database** | SQLite WAL trên **Amazon EFS** *(Terraform tự khóa `1` backend writer)* | SQLite WAL trên **Amazon EFS** *(Terraform tự khóa `1` backend writer)* | **Amazon RDS PostgreSQL 16** Multi-AZ (`db.t4g.small`, backup 14 ngày, deletion protection) |
| **X Simulator nội bộ** | **`enable_x_simulator = true`** (`http://x-simulator.genai-fde-dev.local:8099/2`) | **`enable_x_simulator = true`** *(dự phòng qua Cloud Map DNS)* | **`enable_x_simulator = false`** *(tắt hoàn toàn)* |
| **Chính sách gửi DM** | `DISPATCH_MODE=SANDBOX` cứng | `DISPATCH_MODE=SANDBOX` + `LIVE_X_DRY_RUN=true` + `ALLOWED_TEST_HANDLES` | `DISPATCH_MODE=LIVE_X` + `LIVE_X_DRY_RUN=false` + `ALLOWED_TEST_HANDLES` |
| **Session & Monitoring** | JWT `10080m` (7d), Log `7` ngày | JWT `1440m` (24h), Log `14` ngày, Alarms `true` | JWT `480m` (8h), Log `90` ngày, Alarms `true` |

> **Chú ý cho `staging` (`HYBRID_AUTO`):** `HYBRID_AUTO` cho phép chạy ngay cả khi chưa nạp đủ mọi API key. Trước khi promote lên `prod`, hãy gọi `GET https://staging.scout.genaifund.ai/api/system/runtime` để xác nhận `"live_production_readiness": { "ready": true }` (hoặc test 1 vòng với `RUNTIME_PROFILE=LIVE_PRODUCTION`) nhằm chắc chắn không tồn tại silent fallback.

### 4.2. Quy trình Deploy AWS từng bước cho môi trường mục tiêu (PowerShell, `<env>` = `dev` | `staging` | `prod`)

**Bước 0 — Cài đặt & kiểm tra CLI trên Windows:**
```powershell
# Cài Terraform CLI >= 1.6.0 (chỉ 1 lần đầu)
winget install --id Hashicorp.Terraform -e --accept-source-agreements --accept-package-agreements
# Mở cửa sổ PowerShell mới (hoặc nạp lại PATH ngay trong terminal hiện tại):
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

terraform version
aws sts get-caller-identity   # Xác nhận đúng AWS Account & region ap-southeast-1
```

**Bước 1 — `terraform init` & tạo 2 kho Amazon ECR trước (bắt buộc ở lần deploy đầu):**
Vì ECS Fargate sẽ kéo `:latest` ngay lúc khởi tạo service, ở lần đầu tiên của mỗi môi trường hãy tạo 2 ECR repository trước để tránh lỗi thiếu image:
```powershell
cd d:\AssignmentFDE\infra\terraform
terraform init   # (Xem backend.tf.example nếu muốn dùng S3 Remote State + DynamoDB Lock)
terraform plan -var-file="environments/dev.tfvars"

terraform apply -var-file="environments/dev.tfvars" `
  -target="module.ecs_cluster.aws_ecr_repository.backend" `
  -target="module.ecs_cluster.aws_ecr_repository.frontend"
```

**Bước 2 — Build & Push Docker Image lên Amazon ECR:**
*(Trên Windows PowerShell 5.1, luôn bọc `aws ecr get-login-password | docker login` trong `cmd /c` để tránh lỗi `400 Bad Request` do pipeline PowerShell thêm ký tự xuống dòng/encoding.)*
```powershell
cd d:\AssignmentFDE

$REGION   = "ap-southeast-1"
$BE_REPO  = terraform -chdir=infra/terraform output -raw ecr_backend_repository_url
$FE_REPO  = terraform -chdir=infra/terraform output -raw ecr_frontend_repository_url
$ECR_HOST = $BE_REPO.Split("/")[0]

cmd /c "aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_HOST"

docker build -f backend/Dockerfile -t "${BE_REPO}:latest" .
docker push "${BE_REPO}:latest"

docker build -f frontend/Dockerfile --build-arg NEXT_PUBLIC_API_BASE_URL=auto -t "${FE_REPO}:latest" ./frontend
docker push "${FE_REPO}:latest"
```

**Bước 3 — `terraform apply` toàn bộ hạ tầng `<env>`:**
```powershell
cd d:\AssignmentFDE\infra\terraform
terraform apply -var-file="environments/dev.tfvars"   # hoặc staging.tfvars / prod.tfvars
```
> **Về tên miền & chi phí ở `dev`/`staging`:** Output `app_url = "http://dev.scout.genaifund.ai"` chỉ là chuỗi cấu hình/CORS và **không tạo Route53 hay tốn tiền mua domain**. Sau khi `apply` xong, truy cập trực tiếp bằng **`http://<alb_dns_name>`** (miễn phí từ AWS ALB). Chỉ khi chạy `prod` HTTPS thật mới cần gắn `acm_certificate_arn` và trỏ domain.

**Bước 4 — Nạp Secrets vào AWS Secrets Manager (`<env>/genai-fde/app-secrets`):**
- Với **`dev` (`OFFLINE_MOCK`)**: **không cần chạy bước này** (Terraform đã tự sinh sẵn `SECRET_KEY` ngẫu nhiên 48 ký tự).
- Với **`staging` (`HYBRID_AUTO`)** và **`prod` (`LIVE_PRODUCTION`)**: nạp key thật qua AWS CLI rồi force rollout lại ECS *(tuyệt đối không lưu key trong Git hoặc `.tfvars`)*:
```powershell
aws secretsmanager put-secret-value `
  --region ap-southeast-1 `
  --secret-id staging/genai-fde/app-secrets `
  --secret-string '{"SECRET_KEY":"<random-48-char>","GEMINI_API_KEY":"<key>","OPENAI_API_KEY":"","X_BEARER_TOKEN":"<bearer>","X_API_KEY":"<oauth-key>","X_API_SECRET":"<oauth-secret>","X_ACCESS_TOKEN":"<oauth-token>","X_ACCESS_TOKEN_SECRET":"<oauth-token-secret>"}'

aws ecs update-service --region ap-southeast-1 --cluster genai-fde-staging-cluster --service genai-fde-staging-backend --force-new-deployment
```

**Bước 5 — Kiểm tra ECS Healthy, `/api/system/runtime` & Dọn dẹp (`destroy`):**
```powershell
$ALB_DNS = terraform -chdir=d:\AssignmentFDE\infra\terraform output -raw alb_dns_name
Write-Output "App URL: http://$ALB_DNS/login"

aws ecs describe-services --region ap-southeast-1 --cluster genai-fde-dev-cluster `
  --services genai-fde-dev-backend genai-fde-dev-frontend genai-fde-dev-x-simulator `
  --query "services[*].{Name:serviceName,Desired:desiredCount,Running:runningCount,Status:status}" --output table

curl.exe "http://$ALB_DNS/api/health"
curl.exe "http://$ALB_DNS/api/system/runtime"
# (Trên staging: kiểm tra live_production_readiness.ready == true trước khi cutover prod)
```
```powershell
# Khi test xong muốn dừng tính phí AWS (NAT Gateway, ALB, Fargate Spot, EFS):
cd d:\AssignmentFDE\infra\terraform
terraform destroy -var-file="environments/dev.tfvars"
```

*(Hoặc chạy CI/CD tự động qua GitHub Actions: [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml) — chi tiết module xem thêm tại [`infra/README.md`](infra/README.md).)*

---

## 5. Công cụ CLI Reset Dữ liệu, Kiểm chứng Live Key & Manual QA

### 5.1. Reset Dữ liệu Sạch Chỉ Giữ User Đăng nhập *(Khuyên dùng trước Manual Check)*

```powershell
# Xóa job_queue, outreach_ledger, candidates; giữ Partner (partner@genaifund.ai / GenAIFund2026!)
python -m backend.reset_clean_users --yes

# Giữ Partner + tạo thêm Analyst (analyst@genaifund.ai / Analyst2026!) để test chặn quyền /403
python -m backend.reset_clean_users --yes --with-analyst

# Hoặc nạp sẵn 20 profiles mẫu + 4 historical ledger records:
python backend/seed_data.py
```

### 5.2. Kiểm chứng Live AI & Live X Key (`verify_live_keys.py`)

```powershell
# Gate L1 + L2 + L3 tổng hợp
python -m backend.scripts.verify_live_keys --mode all

# Benchmark chấm điểm THẬT bằng Gemini/OpenAI trên 19 hồ sơ unique & đo Alignment %
python -m backend.scripts.verify_live_keys --mode llm --full-benchmark --json-out tests/manual/results/live-verify-report.json

# Kiểm tra tra cứu X API v2 thật với 1 handle
python -m backend.scripts.verify_live_keys --mode x --handle OpenAI

# Kiểm tra chốt chặn whitelist LIVE_X (Dry-run an toàn)
python -m backend.scripts.verify_live_keys --mode dispatch

# (Tùy chọn) Gửi 1 DM test thật tới handle đã có trong ALLOWED_TEST_HANDLES
python -m backend.scripts.verify_live_keys --mode dispatch --execute-send --dm-handle <handle_trong_whitelist>
```

### 5.3. Luồng Manual QA Nhanh trên Giao diện ([`tests/manual/MANUAL_QA_CHECKLIST.md`](tests/manual/MANUAL_QA_CHECKLIST.md))

1. **Login & Workspace (`/login` $\rightarrow$ `/`):** Kiểm tra khối KPI thu gọn mặc định (`Show Metrics` / `Hide Metrics`) và badge sidebar `Candidate Review`.
2. **Ingestion 3 tab (`/ingestion`):** Test `X Lookup` (nhận diện Simulator hoặc Live mode), `Starter Pack` (20 rows, gộp `P002`/`P020`), và `CSV Import` (Pre-flight column status + 5-row preview, thử `missing_bio.csv`).
3. **Review & Dispatch (`/`):** Bấm `Process Queue`, kiểm tra `ScorePill` 1 dòng (`4 / 4`), highlight trích dẫn vàng trong modal Review, `P017` Prompt Injection (`1 / 4`, DM rỗng), `P018` Sparse (`INSUFFICIENT_EVIDENCE`), `P019` khóa gửi (`422`), và khóa chống gửi đúp (`409`) sau khi `Approve & Send DM`.
4. **Ledger, Calibration & i18n (`/ledger`, `/calibration`):** Kiểm tra `Log Reply` $\rightarrow$ badge `URGENT` $\rightarrow$ `Mark Handled`, bảng `Partner Calibration Matrix` (`100%` alignment), và nút đổi ngôn ngữ **`EN` $\leftrightarrow$ `VI`**.

---

## 6. Bộ Kiểm thử Tự động 3 Tầng & E/R Result Contract

Các bộ test chạy hoàn toàn cô lập (`sqlite:///:memory:` và `outreach_e2e.db` ở cổng `3100`/`8001`/`8099`), **không ghi đè** `outreach.db` và **không tốn tiền API**:

```powershell
# Kiểm tra TypeScript Frontend (không ảnh hưởng .next dev server)
cd frontend; npx.cmd tsc --noEmit; cd ..

# Toàn bộ Backend Tests (Unit + Integration + Contracts + RuntimeGateway + Tools)
python -m pytest backend/tests/ -v

# Full Quality Gate 3 tầng (Tier 1: 6 Contracts + Tier 2: 9 Playwright E2E + Tier 3: E/R Result Contract)
# Lưu ý: tắt terminal x_simulator (:8099) nếu đang mở tay để Playwright tự khởi động ở cổng 8099
powershell -ExecutionPolicy Bypass -File tests/manual/test-all.ps1

# Chạy riêng bước chuyển đổi & đối chiếu E/R Result Contract từ raw traces
python -m backend.scripts.build_er_result_contract
# (Chỉ cập nhật Golden Expected khi chủ đích thay đổi spec E/R):
# python -m backend.scripts.build_er_result_contract --update-expected
```

- Raw telemetry (`tests/manual/results/traces/raw/all-traces.jsonl` & `*.state.json`) được [`backend/scripts/build_er_result_contract.py`](backend/scripts/build_er_result_contract.py) chiếu sang **Result Contract** ([`tests/manual/results/traces/er_result_contract.json`](tests/manual/results/traces/er_result_contract.json)) và `diff` nghiêm ngặt với **Golden Expected** ([`backend/tests/contracts/expected/er_expected_contract.json`](backend/tests/contracts/expected/er_expected_contract.json)) kèm báo cáo [`_ER_CONTRACT_VERIFICATION.md`](tests/manual/results/traces/_ER_CONTRACT_VERIFICATION.md), phủ trọn [`testing/ER-data-packing.md`](testing/ER-data-packing.md), [`testing/ER-F5-F6.md`](testing/ER-F5-F6.md), và 9/9 trạng thái trong [`testing/e2e.md`](testing/e2e.md).

---

## 7. Ghi chú Xử lý Lỗi Thường gặp (Troubleshooting)

| Triệu chứng / Thông báo lỗi | Nguyên nhân | Cách khắc phục |
| :--- | :--- | :--- |
| `ERROR: Error loading ASGI app. Import string "backend.scripts.x_simulator"` | Gõ dư `uvicorn` khi chạy `x_simulator.py` | Dùng `python -m backend.scripts.x_simulator --host 127.0.0.1 --port 8099` hoặc chỉ rõ `:simulator_app`. |
| `HTTP 401 [X API 401 Unauthorized]` dù dùng `sim_dev_bearer_token` | Thiếu `X_API_BASE_URL` trong `.env` (khi ở `HYBRID_AUTO`) hoặc quên restart `uvicorn` | Dùng `RUNTIME_PROFILE=OFFLINE_MOCK`, hoặc thêm `X_API_BASE_URL=http://127.0.0.1:8099/2` rồi restart `uvicorn`. |
| `HTTP 503 [LIVE_PRODUCTION] ...` khi X Lookup hoặc Send DM | Đang bật `LIVE_PRODUCTION` nhưng thiếu API key, trỏ nhầm Simulator/localhost, hoặc `LIVE_X_DRY_RUN=True` | Gọi `GET /api/system/runtime` xem mục `live_production_readiness.missing_requirements` để bổ sung đúng biến còn thiếu. |
| `HTTP 503 Unable to reach X API endpoint (...:8099): [WinError 10061]` | Chưa bật Local X Simulator `:8099` | Chạy `python -m backend.scripts.x_simulator --host 127.0.0.1 --port 8099` ở terminal riêng. |
| `HTTP 402 [X API 402 Payment Required] credits depleted` | Token X thật chưa nạp credit trả phí trên `console.x.com` | Nạp credit Pay-Per-Use hoặc chuyển `RUNTIME_PROFILE=OFFLINE_MOCK` dùng Simulator `$0`. |
| Docker Desktop báo lỗi `dockerDesktopLinuxEngine` không tìm thấy | Docker Desktop chưa được bật | Mở **Docker Desktop** trên Windows và chờ Engine chuyển sang `Running` rồi chạy lại `docker compose`. |
| `terraform : The term 'terraform' is not recognized` sau khi vừa cài `winget` | Terminal trong IDE vẫn giữ `PATH` cũ | Chạy `$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")` hoặc mở lại IDE/terminal mới. |
| `docker login` tới ECR bị `400 Bad Request` trên Windows PowerShell 5.1 | Pipe PowerShell 5.1 thêm CRLF/encoding vào token ~2.200 ký tự | Chạy `docker logout <ecr_host>` rồi bọc lệnh login vào `cmd /c "..."` như ở **Bước 2 (mục 4.2)** thay vì pipe trực tiếp trên PowerShell. |
| Đăng nhập xong trên Docker `http://localhost` nhưng bị đá lại `/login` | Reverse proxy hoặc HTTPS config không khớp `SameSite`/protocol | Dùng đúng profile `--profile prod-sim` qua `http://localhost` (hoặc `:3000`); không chạy thẳng container production behind custom proxy mà thiếu `X-Forwarded-Proto`. |
| `ENOENT ... app-build-manifest.json` trong terminal `next dev` | Chạy `npm run build` trong lúc `next dev` đang mở làm ghi đè `.next` | `Ctrl+C` ở terminal Frontend, `Remove-Item -Recurse -Force .next`, rồi `npm.cmd run dev`. |
| `GET /.well-known/appspecific/com.chrome.devtools.json 404` | Chrome/Edge DevTools (F12) tự dò cấu hình workspace cục bộ | Log vô hại của trình duyệt, hoàn toàn bình thường. |
| `curl` trên PowerShell báo lỗi hoặc trả `401` | PowerShell alias `curl` là `Invoke-WebRequest` hoặc thiếu cookie `-b` | Dùng `curl.exe` trên 1 dòng kèm `-b "session_token=..."`. |
