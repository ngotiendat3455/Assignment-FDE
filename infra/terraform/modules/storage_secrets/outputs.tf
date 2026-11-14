output "app_secrets_arn" {
  value = aws_secretsmanager_secret.app_secrets.arn
}

output "efs_file_system_id" {
  value = var.use_rds ? null : aws_efs_file_system.sqlite_data[0].id
}

output "efs_access_point_id" {
  value = var.use_rds ? null : aws_efs_access_point.sqlite_data[0].id
}

output "rds_endpoint" {
  value = var.use_rds ? aws_db_instance.postgres[0].endpoint : null
}

output "db_url_secret_arn" {
  value = var.use_rds ? aws_secretsmanager_secret.db_url[0].arn : null
}

