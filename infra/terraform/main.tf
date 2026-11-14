locals {
  name_prefix = "${var.project_name}-${var.environment}"

  # Enforce single backend writer when running SQLite WAL on EFS (use_rds = false)
  effective_backend_desired_count = var.use_rds ? var.backend_desired_count : 1
  effective_autoscaling           = var.use_rds && var.enable_autoscaling

  app_scheme = var.acm_certificate_arn != "" ? "https" : "http"
  cors_origins = join(",", [
    "${local.app_scheme}://${var.domain_name}",
    "http://${module.alb.alb_dns_name}"
  ])
}

module "network" {
  source = "./modules/network"

  name_prefix        = local.name_prefix
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  enable_nat_gateway = var.enable_nat_gateway
}

module "alb" {
  source = "./modules/alb"

  name_prefix              = local.name_prefix
  vpc_id                   = module.network.vpc_id
  public_subnet_ids        = module.network.public_subnet_ids
  alb_security_group_id    = module.network.alb_security_group_id
  acm_certificate_arn      = var.acm_certificate_arn
  enable_cloudwatch_alarms = var.enable_cloudwatch_alarms
}

module "storage_secrets" {
  source = "./modules/storage_secrets"

  name_prefix               = local.name_prefix
  environment               = var.environment
  vpc_id                    = module.network.vpc_id
  private_subnet_ids        = module.network.private_subnet_ids
  efs_security_group_id     = module.network.efs_security_group_id
  rds_security_group_id     = module.network.rds_security_group_id
  use_rds                   = var.use_rds
  rds_instance_class        = var.rds_instance_class
  rds_multi_az              = var.rds_multi_az
  rds_backup_retention_days = var.rds_backup_retention_days
  rds_deletion_protection   = var.rds_deletion_protection
}

module "ecs_cluster" {
  source = "./modules/ecs_cluster"

  name_prefix                 = local.name_prefix
  aws_region                  = var.aws_region
  environment                 = var.environment
  vpc_id                      = module.network.vpc_id
  private_subnet_ids          = module.network.private_subnet_ids
  ecs_security_group_id       = module.network.ecs_security_group_id
  frontend_target_group_arn   = module.alb.frontend_target_group_arn
  backend_target_group_arn    = module.alb.backend_target_group_arn
  runtime_profile             = var.runtime_profile
  dispatch_mode               = var.dispatch_mode
  live_x_dry_run              = var.live_x_dry_run
  allowed_test_handles        = var.allowed_test_handles
  gemini_model                = var.gemini_model
  enable_x_simulator          = var.enable_x_simulator
  cors_origins                = local.cors_origins
  access_token_expire_minutes = var.access_token_expire_minutes
  use_rds                     = var.use_rds
  efs_file_system_id          = module.storage_secrets.efs_file_system_id
  efs_access_point_id         = module.storage_secrets.efs_access_point_id
  app_secrets_arn             = module.storage_secrets.app_secrets_arn
  db_url_secret_arn           = module.storage_secrets.db_url_secret_arn
  image_tag                   = var.image_tag
  frontend_cpu                = var.frontend_cpu
  frontend_memory             = var.frontend_memory
  frontend_desired_count      = var.frontend_desired_count
  backend_cpu                 = var.backend_cpu
  backend_memory              = var.backend_memory
  backend_desired_count       = local.effective_backend_desired_count
  use_fargate_spot            = var.use_fargate_spot
  enable_autoscaling          = local.effective_autoscaling
  log_retention_days          = var.log_retention_days
}

