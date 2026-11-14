# ------------------------------------------------------------------------------
# Amazon ECR Repositories & Image Cleanup Policies
# ------------------------------------------------------------------------------
resource "aws_ecr_repository" "backend" {
  name                 = "${var.name_prefix}-backend"
  image_tag_mutability = "MUTABLE"
  force_delete         = var.environment != "prod"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "frontend" {
  name                 = "${var.name_prefix}-frontend"
  image_tag_mutability = "MUTABLE"
  force_delete         = var.environment != "prod"

  image_scanning_configuration {
    scan_on_push = true
  }
}

locals {
  ecr_lifecycle_policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Retain last 10 container images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

resource "aws_ecr_lifecycle_policy" "backend" {
  repository = aws_ecr_repository.backend.name
  policy     = local.ecr_lifecycle_policy
}

resource "aws_ecr_lifecycle_policy" "frontend" {
  repository = aws_ecr_repository.frontend.name
  policy     = local.ecr_lifecycle_policy
}

# ------------------------------------------------------------------------------
# CloudWatch Log Groups
# ------------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/${var.name_prefix}/backend"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/ecs/${var.name_prefix}/frontend"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "x_simulator" {
  count             = var.enable_x_simulator ? 1 : 0
  name              = "/ecs/${var.name_prefix}/x-simulator"
  retention_in_days = var.log_retention_days
}

# ------------------------------------------------------------------------------
# Private Service Discovery (Cloud Map DNS: <service>.<name_prefix>.local)
# ------------------------------------------------------------------------------
resource "aws_service_discovery_private_dns_namespace" "this" {
  name        = "${var.name_prefix}.local"
  description = "Internal DNS namespace for Next.js BFF -> Backend and Backend -> X Simulator"
  vpc         = var.vpc_id
}

resource "aws_service_discovery_service" "backend" {
  name = "backend"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.this.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}

resource "aws_service_discovery_service" "x_simulator" {
  count = var.enable_x_simulator ? 1 : 0
  name  = "x-simulator"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.this.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}

# ------------------------------------------------------------------------------
# ECS Cluster & Capacity Providers (Fargate / Fargate Spot for dev)
# ------------------------------------------------------------------------------
resource "aws_ecs_cluster" "this" {
  name = "${var.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = var.environment == "prod" ? "enabled" : "disabled"
  }
}

resource "aws_ecs_cluster_capacity_providers" "this" {
  cluster_name = aws_ecs_cluster.this.name

  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = var.use_fargate_spot ? "FARGATE_SPOT" : "FARGATE"
    weight            = 1
    base              = 1
  }
}

# ------------------------------------------------------------------------------
# Least-Privilege IAM Roles for ECS Execution & Application Tasks
# ------------------------------------------------------------------------------
data "aws_iam_policy_document" "ecs_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_task_execution" {
  name               = "${var.name_prefix}-ecs-exec-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_base" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

locals {
  readable_secret_arns = var.db_url_secret_arn != null && var.db_url_secret_arn != "" ? [
    var.app_secrets_arn,
    var.db_url_secret_arn,
  ] : [var.app_secrets_arn]
}

data "aws_iam_policy_document" "ecs_secrets_read" {
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = local.readable_secret_arns
  }
}

resource "aws_iam_role_policy" "ecs_secrets_read" {
  name   = "${var.name_prefix}-ecs-secrets-read"
  role   = aws_iam_role.ecs_task_execution.id
  policy = data.aws_iam_policy_document.ecs_secrets_read.json
}

resource "aws_iam_role" "ecs_task" {
  name               = "${var.name_prefix}-ecs-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
}

# ------------------------------------------------------------------------------
# Backend ECS Task Definition & Service
# ------------------------------------------------------------------------------
locals {
  backend_base_secrets = [
    { name = "SECRET_KEY", valueFrom = "${var.app_secrets_arn}:SECRET_KEY::" },
    { name = "GEMINI_API_KEY", valueFrom = "${var.app_secrets_arn}:GEMINI_API_KEY::" },
    { name = "OPENAI_API_KEY", valueFrom = "${var.app_secrets_arn}:OPENAI_API_KEY::" },
    { name = "X_BEARER_TOKEN", valueFrom = "${var.app_secrets_arn}:X_BEARER_TOKEN::" },
    { name = "X_API_KEY", valueFrom = "${var.app_secrets_arn}:X_API_KEY::" },
    { name = "X_API_SECRET", valueFrom = "${var.app_secrets_arn}:X_API_SECRET::" },
    { name = "X_ACCESS_TOKEN", valueFrom = "${var.app_secrets_arn}:X_ACCESS_TOKEN::" },
    { name = "X_ACCESS_TOKEN_SECRET", valueFrom = "${var.app_secrets_arn}:X_ACCESS_TOKEN_SECRET::" },
  ]

  backend_secrets = var.use_rds ? concat(local.backend_base_secrets, [
    { name = "DATABASE_URL", valueFrom = "${var.db_url_secret_arn}:DATABASE_URL::" }
  ]) : local.backend_base_secrets

  backend_env = concat(
    [
      { name = "PORT", value = "8000" },
      { name = "HOST", value = "0.0.0.0" },
      { name = "DEBUG", value = "False" },
      { name = "RUNTIME_PROFILE", value = var.runtime_profile },
      { name = "DISPATCH_MODE", value = var.dispatch_mode },
      { name = "LIVE_X_DRY_RUN", value = tostring(var.live_x_dry_run) },
      { name = "ALLOWED_TEST_HANDLES", value = var.allowed_test_handles },
      { name = "GEMINI_MODEL", value = var.gemini_model },
      { name = "X_API_BASE_URL", value = "https://api.twitter.com/2" },
      { name = "X_SIMULATOR_BASE_URL", value = "http://x-simulator.${var.name_prefix}.local:8099/2" },
      { name = "CORS_ORIGINS", value = var.cors_origins },
      { name = "ACCESS_TOKEN_EXPIRE_MINUTES", value = tostring(var.access_token_expire_minutes) },
    ],
    var.use_rds ? [] : [
      { name = "DATABASE_URL", value = "sqlite:////app/data/outreach.db" }
    ]
  )
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.name_prefix}-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.backend_cpu
  memory                   = var.backend_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  dynamic "volume" {
    for_each = var.use_rds ? [] : [1]
    content {
      name = "sqlite-data"

      efs_volume_configuration {
        file_system_id     = var.efs_file_system_id
        transit_encryption = "ENABLED"

        authorization_config {
          access_point_id = var.efs_access_point_id
          iam             = "DISABLED"
        }
      }
    }
  }

  container_definitions = jsonencode([
    {
      name      = "backend"
      image     = "${aws_ecr_repository.backend.repository_url}:${var.image_tag}"
      essential = true
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]
      environment = local.backend_env
      secrets     = local.backend_secrets
      mountPoints = var.use_rds ? [] : [
        {
          sourceVolume  = "sqlite-data"
          containerPath = "/app/data"
          readOnly      = false
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.backend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "backend" {
  name            = "${var.name_prefix}-backend"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.backend_desired_count

  capacity_provider_strategy {
    capacity_provider = var.use_fargate_spot ? "FARGATE_SPOT" : "FARGATE"
    weight            = 1
  }

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.backend_target_group_arn
    container_name   = "backend"
    container_port   = 8000
  }

  service_registries {
    registry_arn = aws_service_discovery_service.backend.arn
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
}

# ------------------------------------------------------------------------------
# Frontend Next.js BFF ECS Task Definition & Service
# ------------------------------------------------------------------------------
resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.name_prefix}-frontend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.frontend_cpu
  memory                   = var.frontend_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "frontend"
      image     = "${aws_ecr_repository.frontend.repository_url}:${var.image_tag}"
      essential = true
      portMappings = [
        {
          containerPort = 3000
          hostPort      = 3000
          protocol      = "tcp"
        }
      ]
      environment = [
        { name = "NODE_ENV", value = "production" },
        { name = "PORT", value = "3000" },
        { name = "HOSTNAME", value = "0.0.0.0" },
        { name = "BACKEND_INTERNAL_URL", value = "http://backend.${var.name_prefix}.local:8000/api" },
        { name = "NEXT_PUBLIC_API_BASE_URL", value = "/api" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.frontend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "frontend" {
  name            = "${var.name_prefix}-frontend"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = var.frontend_desired_count

  capacity_provider_strategy {
    capacity_provider = var.use_fargate_spot ? "FARGATE_SPOT" : "FARGATE"
    weight            = 1
  }

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.frontend_target_group_arn
    container_name   = "frontend"
    container_port   = 3000
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
}

# ------------------------------------------------------------------------------
# Optional Internal X Simulator Service (dev OFFLINE_MOCK / staging HYBRID_AUTO)
# ------------------------------------------------------------------------------
resource "aws_ecs_task_definition" "x_simulator" {
  count = var.enable_x_simulator ? 1 : 0

  family                   = "${var.name_prefix}-x-simulator"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "x-simulator"
      image     = "${aws_ecr_repository.backend.repository_url}:${var.image_tag}"
      essential = true
      command   = ["python", "-m", "backend.scripts.x_simulator", "--host", "0.0.0.0", "--port", "8099"]
      portMappings = [
        {
          containerPort = 8099
          hostPort      = 8099
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.x_simulator[0].name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "x_simulator" {
  count = var.enable_x_simulator ? 1 : 0

  name            = "${var.name_prefix}-x-simulator"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.x_simulator[0].arn
  desired_count   = 1

  capacity_provider_strategy {
    capacity_provider = var.use_fargate_spot ? "FARGATE_SPOT" : "FARGATE"
    weight            = 1
  }

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.x_simulator[0].arn
  }
}

# ------------------------------------------------------------------------------
# Production AutoScaling (Activated when use_rds=true & enable_autoscaling=true)
# ------------------------------------------------------------------------------
resource "aws_appautoscaling_target" "backend" {
  count = var.enable_autoscaling ? 1 : 0

  max_capacity       = 6
  min_capacity       = var.backend_desired_count
  resource_id        = "service/${aws_ecs_cluster.this.name}/${aws_ecs_service.backend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "backend_cpu" {
  count = var.enable_autoscaling ? 1 : 0

  name               = "${var.name_prefix}-backend-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.backend[0].resource_id
  scalable_dimension = aws_appautoscaling_target.backend[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.backend[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 120
    scale_out_cooldown = 60
  }
}

resource "aws_appautoscaling_target" "frontend" {
  count = var.enable_autoscaling ? 1 : 0

  max_capacity       = 6
  min_capacity       = var.frontend_desired_count
  resource_id        = "service/${aws_ecs_cluster.this.name}/${aws_ecs_service.frontend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "frontend_cpu" {
  count = var.enable_autoscaling ? 1 : 0

  name               = "${var.name_prefix}-frontend-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.frontend[0].resource_id
  scalable_dimension = aws_appautoscaling_target.frontend[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.frontend[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 120
    scale_out_cooldown = 60
  }
}
