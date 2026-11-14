# ==============================================================================
# STAGING Environment — Mapped to RUNTIME_PROFILE = HYBRID_AUTO (Pre-Prod QA)
# Deploy: terraform apply -var-file="environments/staging.tfvars"
# ==============================================================================

project_name    = "genai-fde"
aws_region      = "ap-southeast-1"
environment     = "staging"
runtime_profile = "HYBRID_AUTO"

domain_name         = "staging.scout.genaifund.ai"
acm_certificate_arn = "" # Attach *.scout.genaifund.ai ACM cert ARN before Go-Live

# Flexible Pre-Prod: uses live Gemini if key exists in Secrets Manager, else $0 rubric;
# X DM stays safe via SANDBOX default (enable LIVE_X dry-run only against whitelisted test handles)
dispatch_mode        = "SANDBOX"
live_x_dry_run       = true
allowed_test_handles = "linhtran_robo,minh_quant,test_builder_sea"
enable_x_simulator   = true

# Persistence: Single-task SQLite WAL backed by Amazon EFS (/app/data)
use_rds                = false
frontend_cpu           = 256
frontend_memory        = 512
frontend_desired_count = 1
backend_cpu            = 512
backend_memory         = 1024
backend_desired_count  = 1
use_fargate_spot       = false
enable_autoscaling     = false

access_token_expire_minutes = 1440 # 24 hours
log_retention_days          = 14
enable_cloudwatch_alarms    = true

