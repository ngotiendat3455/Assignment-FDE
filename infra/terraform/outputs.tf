output "environment" {
  description = "Deployed environment name."
  value       = var.environment
}

output "runtime_profile" {
  description = "Active RuntimeGateway profile enforced in ECS backend."
  value       = var.runtime_profile
}

output "app_url" {
  description = "Configured domain URL (and ALB endpoint for verification)."
  value       = "${var.acm_certificate_arn != "" ? "https" : "http"}://${var.domain_name}"
}

output "alb_dns_name" {
  description = "Application Load Balancer public DNS name."
  value       = module.alb.alb_dns_name
}

output "ecr_backend_repository_url" {
  description = "ECR URL for FastAPI backend Docker image."
  value       = module.ecs_cluster.ecr_backend_repository_url
}

output "ecr_frontend_repository_url" {
  description = "ECR URL for Next.js frontend Docker image."
  value       = module.ecs_cluster.ecr_frontend_repository_url
}

output "ecs_cluster_name" {
  description = "Amazon ECS Cluster name."
  value       = module.ecs_cluster.ecs_cluster_name
}

output "database_engine" {
  description = "Active persistence layer (RDS PostgreSQL or EFS SQLite WAL)."
  value       = var.use_rds ? "Amazon RDS PostgreSQL" : "SQLite WAL on Amazon EFS"
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint (null when use_rds=false)."
  value       = module.storage_secrets.rds_endpoint
}

output "app_secrets_arn" {
  description = "AWS Secrets Manager ARN where API keys (GEMINI_API_KEY, X_BEARER_TOKEN, OAuth 1.0a) are stored."
  value       = module.storage_secrets.app_secrets_arn
}

