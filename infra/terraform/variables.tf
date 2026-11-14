variable "project_name" {
  description = "Short slug identifying this workload across AWS resources."
  type        = string
  default     = "genai-fde"
}

variable "aws_region" {
  description = "AWS region for deployment (default Singapore ap-southeast-1 for SEA low latency)."
  type        = string
  default     = "ap-southeast-1"
}

variable "environment" {
  description = "Target deployment environment (dev | staging | prod)."
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "runtime_profile" {
  description = "Centralized RuntimeGateway profile mapped 1-to-1 with environment: OFFLINE_MOCK (dev), HYBRID_AUTO (staging), LIVE_PRODUCTION (prod)."
  type        = string

  validation {
    condition     = contains(["OFFLINE_MOCK", "HYBRID_AUTO", "LIVE_PRODUCTION"], var.runtime_profile)
    error_message = "runtime_profile must be one of: OFFLINE_MOCK, HYBRID_AUTO, LIVE_PRODUCTION."
  }
}

# ------------------------------------------------------------------------------
# Networking
# ------------------------------------------------------------------------------
variable "vpc_cidr" {
  description = "CIDR block for the environment VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "availability_zones" {
  description = "Two AZs for multi-AZ ALB, subnets, and optional RDS."
  type        = list(string)
  default     = ["ap-southeast-1a", "ap-southeast-1b"]
}

variable "enable_nat_gateway" {
  description = "Provision a single NAT Gateway for Private Subnet egress (Gemini/OpenAI/X API & ECR pulls)."
  type        = bool
  default     = true
}

# ------------------------------------------------------------------------------
# Ingress & Domain
# ------------------------------------------------------------------------------
variable "domain_name" {
  description = "Public hostname for this environment (used for CORS_ORIGINS and reference outputs)."
  type        = string
}

variable "acm_certificate_arn" {
  description = "ACM HTTPS certificate ARN for ALB :443 listener. Leave empty for HTTP :80 bootstrap smoke deploys."
  type        = string
  default     = ""
}

# ------------------------------------------------------------------------------
# Runtime Safety, AI & X API Controls
# ------------------------------------------------------------------------------
variable "dispatch_mode" {
  description = "Outreach dispatch mode (SANDBOX | LIVE_X)."
  type        = string
  default     = "SANDBOX"

  validation {
    condition     = contains(["SANDBOX", "LIVE_X"], var.dispatch_mode)
    error_message = "dispatch_mode must be SANDBOX or LIVE_X."
  }
}

variable "live_x_dry_run" {
  description = "Keep true on staging to verify LIVE_X whitelist/OAuth flow without sending external DMs."
  type        = bool
  default     = false
}

variable "allowed_test_handles" {
  description = "Comma-separated X handles permitted for LIVE_X dispatch."
  type        = string
  default     = "linhtran_robo,minh_quant,test_builder_sea"
}

variable "gemini_model" {
  description = "Primary Google Gemini model used in HYBRID_AUTO / LIVE_PRODUCTION."
  type        = string
  default     = "gemini-3.5-flash"
}

variable "enable_x_simulator" {
  description = "Run internal X API v2 Simulator ECS service (true for dev OFFLINE_MOCK / staging HYBRID_AUTO)."
  type        = bool
  default     = false
}

# ------------------------------------------------------------------------------
# Database Strategy: EFS SQLite WAL (dev/staging) vs RDS PostgreSQL (prod)
# ------------------------------------------------------------------------------
variable "use_rds" {
  description = "Use Amazon RDS PostgreSQL (true for prod HA multi-task) vs EFS-backed SQLite WAL (false for dev/staging)."
  type        = bool
  default     = false
}

variable "rds_instance_class" {
  description = "RDS PostgreSQL instance size when use_rds=true."
  type        = string
  default     = "db.t4g.micro"
}

variable "rds_multi_az" {
  description = "Enable Multi-AZ standby for RDS PostgreSQL in production."
  type        = bool
  default     = false
}

variable "rds_backup_retention_days" {
  description = "Automated snapshot retention period for RDS."
  type        = number
  default     = 7
}

variable "rds_deletion_protection" {
  description = "Protect RDS instance from accidental deletion in production."
  type        = bool
  default     = false
}

# ------------------------------------------------------------------------------
# ECS Fargate Compute & Scaling
# ------------------------------------------------------------------------------
variable "image_tag" {
  description = "Container image tag deployed to FE and BE ECS tasks."
  type        = string
  default     = "latest"
}

variable "frontend_cpu" {
  description = "Fargate CPU units for Next.js frontend task."
  type        = number
  default     = 256
}

variable "frontend_memory" {
  description = "Fargate memory (MiB) for Next.js frontend task."
  type        = number
  default     = 512
}

variable "frontend_desired_count" {
  description = "Desired ECS task count for Next.js frontend."
  type        = number
  default     = 1
}

variable "backend_cpu" {
  description = "Fargate CPU units for FastAPI backend task."
  type        = number
  default     = 256
}

variable "backend_memory" {
  description = "Fargate memory (MiB) for FastAPI backend task."
  type        = number
  default     = 512
}

variable "backend_desired_count" {
  description = "Desired ECS task count for FastAPI backend (must be 1 when use_rds=false / SQLite EFS)."
  type        = number
  default     = 1
}

variable "use_fargate_spot" {
  description = "Prefer FARGATE_SPOT capacity provider for non-production cost optimization."
  type        = bool
  default     = false
}

variable "enable_autoscaling" {
  description = "Enable ECS Application AutoScaling (CPU target tracking, recommended only in prod with use_rds=true)."
  type        = bool
  default     = false
}

variable "access_token_expire_minutes" {
  description = "JWT session lifetime in minutes."
  type        = number
  default     = 1440
}

# ------------------------------------------------------------------------------
# Observability
# ------------------------------------------------------------------------------
variable "log_retention_days" {
  description = "CloudWatch Logs retention window in days (7 dev, 14 staging, 90 prod)."
  type        = number
  default     = 14
}

variable "enable_cloudwatch_alarms" {
  description = "Provision CloudWatch 5xx and Unhealthy Target alarms."
  type        = bool
  default     = true
}

