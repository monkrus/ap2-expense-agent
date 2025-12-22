variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "project_name" {
  type        = string
  description = "Project name prefix for resource naming"
}

variable "region" {
  type        = string
  description = "Primary GCP region"
  default     = "us-central1"
}

variable "environment" {
  type        = string
  description = "Deployment environment (development, staging, production)"
  default     = "development"
}

variable "db_tier" {
  type        = string
  description = "Cloud SQL instance tier"
  default     = "db-f1-micro"
}

variable "db_disk_size" {
  type        = number
  description = "Cloud SQL disk size (GB)"
  default     = 20
}

variable "database_name" {
  type        = string
  description = "Database name"
  default     = "ap2_expense"
}

variable "db_user" {
  type        = string
  description = "Database user name"
  default     = "ap2_user"
}

variable "redis_memory_gb" {
  type        = number
  description = "Redis memory size (GB)"
  default     = 1
}

variable "backend_image" {
  type        = string
  description = "Container image for the backend Cloud Run service"
}

variable "frontend_image" {
  type        = string
  description = "Container image for the frontend Cloud Run service"
}

variable "backend_cpu" {
  type        = string
  description = "Backend CPU allocation"
  default     = "2"
}

variable "backend_memory" {
  type        = string
  description = "Backend memory allocation"
  default     = "2Gi"
}

variable "backend_min_instances" {
  type        = number
  description = "Backend minimum instances"
  default     = 1
}

variable "backend_max_instances" {
  type        = number
  description = "Backend maximum instances"
  default     = 10
}

variable "frontend_cpu" {
  type        = string
  description = "Frontend CPU allocation"
  default     = "1"
}

variable "frontend_memory" {
  type        = string
  description = "Frontend memory allocation"
  default     = "512Mi"
}

variable "frontend_min_instances" {
  type        = number
  description = "Frontend minimum instances"
  default     = 0
}

variable "frontend_max_instances" {
  type        = number
  description = "Frontend maximum instances"
  default     = 5
}

variable "allow_unauthenticated" {
  type        = bool
  description = "Allow unauthenticated access to Cloud Run services"
  default     = true
}

variable "backend_env_vars" {
  type        = map(string)
  description = "Extra environment variables for the backend service"
  default     = {}
}

variable "frontend_env_vars" {
  type        = map(string)
  description = "Extra environment variables for the frontend service"
  default     = {}
}

variable "jwt_secret" {
  type        = string
  description = "JWT signing secret"
  sensitive   = true
  default     = null
}

variable "stripe_secret_key" {
  type        = string
  description = "Stripe secret key"
  sensitive   = true
  default     = null
}

variable "gcp_webhook_secret" {
  type        = string
  description = "GCP webhook signature secret"
  sensitive   = true
  default     = null
}

variable "enable_load_balancer" {
  type        = bool
  description = "Enable HTTP load balancer in front of the frontend service"
  default     = false
}
