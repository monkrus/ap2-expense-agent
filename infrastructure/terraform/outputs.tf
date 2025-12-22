output "backend_service_url" {
  description = "Backend Cloud Run service URL"
  value       = google_cloud_run_service.backend.status[0].url
}

output "frontend_service_url" {
  description = "Frontend Cloud Run service URL"
  value       = google_cloud_run_service.frontend.status[0].url
}

output "cloudsql_connection_name" {
  description = "Cloud SQL instance connection name"
  value       = google_sql_database_instance.main.connection_name
}

output "db_password_secret_id" {
  description = "Secret Manager ID for the database password"
  value       = google_secret_manager_secret.db_password.id
}

output "redis_host" {
  description = "Redis instance host"
  value       = google_redis_instance.cache.host
}

output "load_balancer_ip" {
  description = "HTTP load balancer IP (if enabled)"
  value       = var.enable_load_balancer ? google_compute_global_address.lb_ip[0].address : null
}
