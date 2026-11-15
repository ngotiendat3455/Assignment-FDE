# ==============================================================================
# PROD Environment — Identical infra footprint to DEV (EFS SQLite + Fargate Spot),
# differing only in LIVE_PRODUCTION + real Gemini & X API v2 integration.
# Populate real API keys in AWS Secrets Manager (`prod/genai-fde/app-secrets`):
#   GEMINI_API_KEY, X_BEARER_TOKEN, X_API_KEY, X_API_SECRET,
#   X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET (+ optional OPENAI_API_KEY)
# Deploy: terraform apply -var-file="environments/prod.tfvars"
# ==============================================================================

project_name    = "genai-fde"
aws_region      = "ap-southeast-1"
environment     = "prod"
runtime_profile = "LIVE_PRODUCTION"

domain_name         = "scout.xscout.local"
acm_certificate_arn = "" # Optional ACM ARN for HTTPS :443; leave blank for HTTP :80 ALB bootstrap

# Real Gemini LLM + Live X API v2 (no simulator, strict zero fallback)
dispatch_mode        = "LIVE_X"
live_x_dry_run       = false
allowed_test_handles = "dat_ai_test"
gemini_model         = "gemini-3.5-flash"
enable_x_simulator   = false

# Persistence & Compute: Identical to DEV (Single-task SQLite WAL on EFS + Fargate Spot)
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
