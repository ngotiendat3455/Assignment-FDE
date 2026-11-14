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
allowed_test_handles = "linhtran_robo,minh_quant,test_builder_sea"
enable_x_simulator   = false

# Persistence: Multi-AZ Amazon RDS PostgreSQL 16 + Multi-Task AutoScaling ECS Fargate
use_rds                   = true
rds_instance_class        = "db.t4g.small"
rds_multi_az              = true
rds_backup_retention_days = 14
rds_deletion_protection   = true

frontend_cpu           = 512
frontend_memory        = 1024
frontend_desired_count = 2
backend_cpu            = 1024
backend_memory         = 2048
backend_desired_count  = 2
use_fargate_spot       = false
enable_autoscaling     = true

access_token_expire_minutes = 480 # 8 hours hardened session TTL
log_retention_days          = 90
enable_cloudwatch_alarms    = true

