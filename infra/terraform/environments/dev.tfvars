# ==============================================================================
# DEV Environment — Mapped to RUNTIME_PROFILE = OFFLINE_MOCK ($0 External API)
# Deploy: terraform apply -var-file="environments/dev.tfvars"
# ==============================================================================

project_name    = "genai-fde"
aws_region      = "ap-southeast-1"
environment     = "dev"
runtime_profile = "OFFLINE_MOCK"

domain_name         = "dev.scout.xscout.local"
acm_certificate_arn = "" # Provide ACM ARN for HTTPS; leave blank for HTTP :80 ALB bootstrap

# Zero external LLM or X API calls; internal X Simulator handles lookup tests
dispatch_mode      = "SANDBOX"
live_x_dry_run     = false
enable_x_simulator = true

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

