resource "google_compute_global_address" "lb_ip" {
  count = var.enable_load_balancer ? 1 : 0
  name  = "${var.project_name}-lb-ip-${var.environment}"
}

resource "google_compute_region_network_endpoint_group" "frontend_neg" {
  count                 = var.enable_load_balancer ? 1 : 0
  name                  = "${var.project_name}-frontend-neg-${var.environment}"
  region                = var.region
  network_endpoint_type = "SERVERLESS"

  cloud_run {
    service = google_cloud_run_service.frontend.name
  }
}

resource "google_compute_backend_service" "frontend_backend" {
  count                 = var.enable_load_balancer ? 1 : 0
  name                  = "${var.project_name}-frontend-backend-${var.environment}"
  protocol              = "HTTP"
  load_balancing_scheme = "EXTERNAL"

  backend {
    group = google_compute_region_network_endpoint_group.frontend_neg[0].id
  }
}

resource "google_compute_url_map" "frontend_url_map" {
  count          = var.enable_load_balancer ? 1 : 0
  name           = "${var.project_name}-frontend-map-${var.environment}"
  default_service = google_compute_backend_service.frontend_backend[0].id
}

resource "google_compute_target_http_proxy" "frontend_proxy" {
  count   = var.enable_load_balancer ? 1 : 0
  name    = "${var.project_name}-frontend-proxy-${var.environment}"
  url_map = google_compute_url_map.frontend_url_map[0].id
}

resource "google_compute_global_forwarding_rule" "frontend_http" {
  count      = var.enable_load_balancer ? 1 : 0
  name       = "${var.project_name}-frontend-http-${var.environment}"
  ip_address = google_compute_global_address.lb_ip[0].address
  port_range = "80"
  target     = google_compute_target_http_proxy.frontend_proxy[0].id
}
