# ==============================================================================
# PROD Environment — Mapped to RUNTIME_PROFILE = LIVE_PRODUCTION (Strict Zero Fallback)
# Deploy: terraform apply -var-file="environments/prod.tfvars"
# ==============================================================================

project_name    = "genai-fde"
aws_region      = "ap-southeast-1"
environment     = "prod"
runtime_profile = "LIVE_PRODUCTION"

domain_name         = "scout.genaifund.ai"
acm_certificate_arn = "" # REQUIRED for production HTTPS :443 (set real ACM ARN before prod apply)

# Strict Live Execution: requires real GEMINI/OPENAI_API_KEY + X_BEARER_TOKEN + OAuth 1.0a keys
# in AWS Secrets Manager (`prod/genai-fde/app-secrets`); missing keys fail-fast (no mock/sim fallback).
dispatch_mode        = "LIVE_X"
live_x_dry_run       = false
allowed_test_handles = "dat_ai_test"
enable_x_simulator   = false

# Persistence: Single-task SQLite WAL backed by Amazon EFS (/app/data)
use_rds                = false
frontend_cpu           = 256
frontend_memory        = 512
frontend_desired_count = 1
backend_cpu            = 256
backend_memory         = 512
backend_desired_count  = 1
use_fargate_spot       = true
enable_autoscaling     = false

access_token_expire_minutes = 10080 # 7 days for smooth QA workflows
log_retention_days          = 7
enable_cloudwatch_alarms    = false
