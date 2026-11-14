resource "random_password" "jwt_secret" {
  length  = 48
  special = false
}

# ------------------------------------------------------------------------------
# AWS Secrets Manager: Application API Keys & JWT Signing Secret
# Operators populate real GEMINI/X keys directly in AWS Console/CLI without
# storing secrets in Git/tfvars; ignore_changes preserves rotated secret values.
# ------------------------------------------------------------------------------
resource "aws_secretsmanager_secret" "app_secrets" {
  name                    = "${var.environment}/genai-fde/app-secrets"
  description             = "JWT SECRET_KEY, LLM keys (Gemini/OpenAI), and X API v2 credentials for ${var.environment}."
  recovery_window_in_days = var.environment == "prod" ? 30 : 0
}

resource "aws_secretsmanager_secret_version" "app_secrets_initial" {
  secret_id = aws_secretsmanager_secret.app_secrets.id
  secret_string = jsonencode({
    SECRET_KEY            = random_password.jwt_secret.result
    GEMINI_API_KEY        = ""
    OPENAI_API_KEY        = ""
    X_BEARER_TOKEN        = ""
    X_API_KEY             = ""
    X_API_SECRET          = ""
    X_ACCESS_TOKEN        = ""
    X_ACCESS_TOKEN_SECRET = ""
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

# ------------------------------------------------------------------------------
# Stage 1 Persistence (dev & staging): Amazon EFS for SQLite WAL (/app/data)
# ------------------------------------------------------------------------------
resource "aws_efs_file_system" "sqlite_data" {
  count = var.use_rds ? 0 : 1

  creation_token   = "${var.name_prefix}-sqlite-efs"
  encrypted        = true
  throughput_mode  = "bursting"
  performance_mode = "generalPurpose"

  tags = {
    Name = "${var.name_prefix}-sqlite-efs"
  }
}

resource "aws_efs_mount_target" "sqlite_data" {
  count = var.use_rds ? 0 : length(var.private_subnet_ids)

  file_system_id  = aws_efs_file_system.sqlite_data[0].id
  subnet_id       = var.private_subnet_ids[count.index]
  security_groups = [var.efs_security_group_id]
}

resource "aws_efs_access_point" "sqlite_data" {
  count = var.use_rds ? 0 : 1

  file_system_id = aws_efs_file_system.sqlite_data[0].id

  posix_user {
    uid = 1001
    gid = 1001
  }

  root_directory {
    path = "/app/data"
    creation_info {
      owner_uid   = 1001
      owner_gid   = 1001
      permissions = "0755"
    }
  }

  tags = {
    Name = "${var.name_prefix}-sqlite-ap"
  }
}

# ------------------------------------------------------------------------------
# Stage 2 Persistence (prod HA & multi-writer scaling): Amazon RDS PostgreSQL 16
# ------------------------------------------------------------------------------
resource "random_password" "rds_password" {
  count   = var.use_rds ? 1 : 0
  length  = 32
  special = false
}

resource "aws_db_subnet_group" "postgres" {
  count = var.use_rds ? 1 : 0

  name       = "${var.name_prefix}-db-subnets"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name = "${var.name_prefix}-db-subnets"
  }
}

resource "aws_db_instance" "postgres" {
  count = var.use_rds ? 1 : 0

  identifier     = "${var.name_prefix}-pg"
  engine         = "postgres"
  engine_version = "16"
  instance_class = var.rds_instance_class

  db_name  = "genai_outreach"
  username = "genai_admin"
  password = random_password.rds_password[0].result

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true

  multi_az               = var.rds_multi_az
  publicly_accessible    = false
  db_subnet_group_name   = aws_db_subnet_group.postgres[0].name
  vpc_security_group_ids = [var.rds_security_group_id]

  backup_retention_period   = var.rds_backup_retention_days
  deletion_protection       = var.rds_deletion_protection
  skip_final_snapshot       = var.environment != "prod"
  final_snapshot_identifier = var.environment == "prod" ? "${var.name_prefix}-final-snapshot" : null

  tags = {
    Name = "${var.name_prefix}-pg"
  }
}

resource "aws_secretsmanager_secret" "db_url" {
  count = var.use_rds ? 1 : 0

  name                    = "${var.environment}/genai-fde/db-url"
  description             = "Managed SQLAlchemy DATABASE_URL for RDS PostgreSQL (${var.environment})."
  recovery_window_in_days = var.environment == "prod" ? 30 : 0
}

resource "aws_secretsmanager_secret_version" "db_url" {
  count = var.use_rds ? 1 : 0

  secret_id = aws_secretsmanager_secret.db_url[0].id
  secret_string = jsonencode({
    DATABASE_URL = "postgresql+psycopg://${aws_db_instance.postgres[0].username}:${random_password.rds_password[0].result}@${aws_db_instance.postgres[0].endpoint}/${aws_db_instance.postgres[0].db_name}"
  })
}

