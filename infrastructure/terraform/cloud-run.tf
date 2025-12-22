resource "google_service_account" "cloud_run" {
  account_id   = "${var.project_name}-run"
  display_name = "Cloud Run service account"
}

resource "google_cloud_run_service" "backend" {
  name     = "${var.project_name}-backend-${var.environment}"
  location = var.region

  template {
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale"      = tostring(var.backend_min_instances)
        "autoscaling.knative.dev/maxScale"      = tostring(var.backend_max_instances)
        "run.googleapis.com/cloudsql-instances" = google_sql_database_instance.main.connection_name
      }
    }
    spec {
      service_account_name = google_service_account.cloud_run.email
      containers {
        image = var.backend_image
        resources {
          limits = {
            cpu    = var.backend_cpu
            memory = var.backend_memory
          }
        }
        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }
        dynamic "env" {
          for_each = var.backend_env_vars
          content {
            name  = env.key
            value = env.value
          }
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  autogenerate_revision_name = true

  depends_on = [google_project_service.required_apis]
}

resource "google_cloud_run_service_iam_member" "backend_invoker" {
  count    = var.allow_unauthenticated ? 1 : 0
  location = google_cloud_run_service.backend.location
  service  = google_cloud_run_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service" "frontend" {
  name     = "${var.project_name}-frontend-${var.environment}"
  location = var.region

  template {
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = tostring(var.frontend_min_instances)
        "autoscaling.knative.dev/maxScale" = tostring(var.frontend_max_instances)
      }
    }
    spec {
      service_account_name = google_service_account.cloud_run.email
      containers {
        image = var.frontend_image
        resources {
          limits = {
            cpu    = var.frontend_cpu
            memory = var.frontend_memory
          }
        }
        dynamic "env" {
          for_each = var.frontend_env_vars
          content {
            name  = env.key
            value = env.value
          }
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  autogenerate_revision_name = true

  depends_on = [google_project_service.required_apis]
}

resource "google_cloud_run_service_iam_member" "frontend_invoker" {
  count    = var.allow_unauthenticated ? 1 : 0
  location = google_cloud_run_service.frontend.location
  service  = google_cloud_run_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
