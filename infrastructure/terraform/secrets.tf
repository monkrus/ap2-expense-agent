locals {
  jwt_secret_provided    = var.jwt_secret != null && var.jwt_secret != ""
  stripe_secret_provided = var.stripe_secret_key != null && var.stripe_secret_key != ""
  gcp_secret_provided    = var.gcp_webhook_secret != null && var.gcp_webhook_secret != ""
}

resource "google_secret_manager_secret" "jwt_secret" {
  count     = local.jwt_secret_provided ? 1 : 0
  secret_id = "${var.project_name}-jwt-secret-${var.environment}"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "jwt_secret" {
  count       = local.jwt_secret_provided ? 1 : 0
  secret      = google_secret_manager_secret.jwt_secret[0].id
  secret_data = var.jwt_secret
}

resource "google_secret_manager_secret" "stripe_secret_key" {
  count     = local.stripe_secret_provided ? 1 : 0
  secret_id = "${var.project_name}-stripe-secret-${var.environment}"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "stripe_secret_key" {
  count       = local.stripe_secret_provided ? 1 : 0
  secret      = google_secret_manager_secret.stripe_secret_key[0].id
  secret_data = var.stripe_secret_key
}

resource "google_secret_manager_secret" "gcp_webhook_secret" {
  count     = local.gcp_secret_provided ? 1 : 0
  secret_id = "${var.project_name}-gcp-webhook-secret-${var.environment}"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "gcp_webhook_secret" {
  count       = local.gcp_secret_provided ? 1 : 0
  secret      = google_secret_manager_secret.gcp_webhook_secret[0].id
  secret_data = var.gcp_webhook_secret
}
