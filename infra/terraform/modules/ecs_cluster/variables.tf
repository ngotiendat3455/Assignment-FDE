variable "name_prefix" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "ecs_security_group_id" {
  type = string
}

variable "frontend_target_group_arn" {
  type = string
}

variable "backend_target_group_arn" {
  type = string
}

variable "runtime_profile" {
  type = string
}

variable "dispatch_mode" {
  type = string
}

variable "live_x_dry_run" {
  type = bool
}

variable "allowed_test_handles" {
  type = string
}

variable "gemini_model" {
  type = string
}

variable "enable_x_simulator" {
  type = bool
}

variable "cors_origins" {
  type = string
}

variable "access_token_expire_minutes" {
  type = number
}

variable "use_rds" {
  type = bool
}

variable "efs_file_system_id" {
  type    = string
  default = null
}

variable "efs_access_point_id" {
  type    = string
  default = null
}

variable "app_secrets_arn" {
  type = string
}

variable "db_url_secret_arn" {
  type    = string
  default = null
}

variable "image_tag" {
  type = string
}

variable "frontend_cpu" {
  type = number
}

variable "frontend_memory" {
  type = number
}

variable "frontend_desired_count" {
  type = number
}

variable "backend_cpu" {
  type = number
}

variable "backend_memory" {
  type = number
}

variable "backend_desired_count" {
  type = number
}

variable "use_fargate_spot" {
  type = bool
}

variable "enable_autoscaling" {
  type = bool
}

variable "log_retention_days" {
  type = number
}

