"""
Monitoring and Observability
Provides metrics, health checks, and performance monitoring
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from fastapi.responses import PlainTextResponse
import time
import psutil
import os
from typing import Callable
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Prometheus Metrics
# ============================================================================

# HTTP metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'HTTP requests currently being processed'
)

# Database metrics
db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation']
)

db_connections_total = Gauge(
    'db_connections_total',
    'Current number of database connections'
)

# Cache metrics
cache_hits_total = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

# Business metrics
expenses_created_total = Counter(
    'expenses_created_total',
    'Total expenses created',
    ['organization_id']
)

expenses_approved_total = Counter(
    'expenses_approved_total',
    'Total expenses approved',
    ['organization_id']
)

ap2_payments_total = Counter(
    'ap2_payments_total',
    'Total AP2 payments processed',
    ['status']
)

# System metrics
system_cpu_usage = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage'
)

system_memory_usage = Gauge(
    'system_memory_usage_bytes',
    'System memory usage in bytes'
)

system_disk_usage = Gauge(
    'system_disk_usage_percent',
    'System disk usage percentage'
)


# ============================================================================
# Metrics Middleware
# ============================================================================

async def metrics_middleware(request: Request, call_next: Callable) -> Response:
    """Middleware to collect HTTP metrics"""

    # Skip metrics endpoint itself
    if request.url.path == "/metrics":
        return await call_next(request)

    # Increment in-progress gauge
    http_requests_in_progress.inc()

    # Start timer
    start_time = time.time()

    try:
        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Record metrics
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()

        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)

        return response

    finally:
        # Decrement in-progress gauge
        http_requests_in_progress.dec()


# ============================================================================
# Metrics Endpoint
# ============================================================================

async def metrics_endpoint() -> PlainTextResponse:
    """Expose Prometheus metrics"""
    # Update system metrics
    update_system_metrics()

    return PlainTextResponse(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


def update_system_metrics():
    """Update system resource metrics"""
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        system_cpu_usage.set(cpu_percent)

        # Memory usage
        memory = psutil.virtual_memory()
        system_memory_usage.set(memory.used)

        # Disk usage
        disk = psutil.disk_usage('/')
        system_disk_usage.set(disk.percent)

    except Exception as e:
        logger.error(f"Error updating system metrics: {e}")


# ============================================================================
# Health Checks
# ============================================================================

class HealthCheck:
    """Application health check"""

    @staticmethod
    async def check_database(db_session) -> dict:
        """Check database connectivity"""
        try:
            from sqlalchemy import text
            result = db_session.execute(text("SELECT 1"))
            return {
                "status": "healthy",
                "response_time_ms": 0  # Would need timing
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    @staticmethod
    async def check_redis() -> dict:
        """Check Redis connectivity"""
        try:
            from .cache import cache
            if cache.available:
                cache.redis_client.ping()
                return {"status": "healthy"}
            else:
                return {"status": "unavailable", "message": "Redis not configured"}
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    @staticmethod
    def check_disk_space() -> dict:
        """Check available disk space"""
        try:
            disk = psutil.disk_usage('/')
            return {
                "status": "healthy" if disk.percent < 90 else "warning",
                "used_percent": disk.percent,
                "free_gb": disk.free / (1024 ** 3)
            }
        except Exception as e:
            return {
                "status": "unknown",
                "error": str(e)
            }

    @staticmethod
    def check_memory() -> dict:
        """Check memory usage"""
        try:
            memory = psutil.virtual_memory()
            return {
                "status": "healthy" if memory.percent < 90 else "warning",
                "used_percent": memory.percent,
                "available_gb": memory.available / (1024 ** 3)
            }
        except Exception as e:
            return {
                "status": "unknown",
                "error": str(e)
            }


async def health_check_endpoint(db_session) -> dict:
    """Comprehensive health check endpoint"""
    checks = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": os.getenv("APP_VERSION", "unknown"),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "checks": {}
    }

    # Database check
    checks["checks"]["database"] = await HealthCheck.check_database(db_session)

    # Redis check
    checks["checks"]["redis"] = await HealthCheck.check_redis()

    # System checks
    checks["checks"]["disk"] = HealthCheck.check_disk_space()
    checks["checks"]["memory"] = HealthCheck.check_memory()

    # Determine overall status
    for check_name, check_result in checks["checks"].items():
        if check_result.get("status") == "unhealthy":
            checks["status"] = "unhealthy"
            break
        elif check_result.get("status") == "warning" and checks["status"] != "unhealthy":
            checks["status"] = "degraded"

    return checks


# ============================================================================
# Performance Monitoring
# ============================================================================

class PerformanceMonitor:
    """Monitor and track performance metrics"""

    @staticmethod
    def track_db_query(operation: str, duration: float):
        """Track database query performance"""
        db_query_duration_seconds.labels(operation=operation).observe(duration)

    @staticmethod
    def track_cache_hit(cache_type: str):
        """Track cache hit"""
        cache_hits_total.labels(cache_type=cache_type).inc()

    @staticmethod
    def track_cache_miss(cache_type: str):
        """Track cache miss"""
        cache_misses_total.labels(cache_type=cache_type).inc()

    @staticmethod
    def track_expense_created(organization_id: str):
        """Track expense creation"""
        expenses_created_total.labels(organization_id=organization_id).inc()

    @staticmethod
    def track_expense_approved(organization_id: str):
        """Track expense approval"""
        expenses_approved_total.labels(organization_id=organization_id).inc()

    @staticmethod
    def track_ap2_payment(status: str):
        """Track AP2 payment"""
        ap2_payments_total.labels(status=status).inc()


# ============================================================================
# Uptime Monitoring (External Services)
# ============================================================================

def register_uptime_monitoring():
    """Register with uptime monitoring services"""

    # UptimeRobot
    uptime_robot_api_key = os.getenv("UPTIMEROBOT_API_KEY")
    if uptime_robot_api_key:
        logger.info("UptimeRobot monitoring configured")
        # UptimeRobot polls the health endpoint automatically

    # Pingdom
    pingdom_api_key = os.getenv("PINGDOM_API_KEY")
    if pingdom_api_key:
        logger.info("Pingdom monitoring configured")

    # StatusCake
    statuscake_api_key = os.getenv("STATUSCAKE_API_KEY")
    if statuscake_api_key:
        logger.info("StatusCake monitoring configured")


# ============================================================================
# Application Performance Monitoring (APM)
# ============================================================================

def init_apm():
    """Initialize Application Performance Monitoring"""

    # New Relic
    new_relic_license_key = os.getenv("NEW_RELIC_LICENSE_KEY")
    if new_relic_license_key:
        try:
            import newrelic.agent
            newrelic.agent.initialize()
            logger.info("New Relic APM initialized")
        except ImportError:
            logger.warning("New Relic agent not installed")

    # DataDog
    datadog_api_key = os.getenv("DATADOG_API_KEY")
    if datadog_api_key:
        try:
            from ddtrace import tracer, patch_all
            patch_all()
            logger.info("DataDog APM initialized")
        except ImportError:
            logger.warning("DataDog tracer not installed")


# ============================================================================
# Custom Alerts
# ============================================================================

class AlertManager:
    """Manage custom alerts"""

    @staticmethod
    def send_alert(severity: str, title: str, message: str, details: dict = None):
        """Send alert to configured channels"""

        alert_data = {
            "severity": severity,
            "title": title,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "environment": os.getenv("ENVIRONMENT"),
            "details": details or {}
        }

        # Slack webhook
        slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        if slack_webhook:
            try:
                import requests
                requests.post(slack_webhook, json={
                    "text": f"*{severity.upper()}*: {title}",
                    "attachments": [{
                        "text": message,
                        "color": "danger" if severity == "critical" else "warning"
                    }]
                })
            except Exception as e:
                logger.error(f"Failed to send Slack alert: {e}")

        # PagerDuty
        pagerduty_key = os.getenv("PAGERDUTY_INTEGRATION_KEY")
        if pagerduty_key and severity == "critical":
            try:
                import requests
                requests.post(
                    "https://events.pagerduty.com/v2/enqueue",
                    json={
                        "routing_key": pagerduty_key,
                        "event_action": "trigger",
                        "payload": {
                            "summary": title,
                            "severity": severity,
                            "source": "AP2 Expense Agent",
                            "custom_details": alert_data
                        }
                    }
                )
            except Exception as e:
                logger.error(f"Failed to send PagerDuty alert: {e}")

        # Log alert
        logger.error(
            f"ALERT: {title} - {message}",
            extra=alert_data
        )

    @staticmethod
    def alert_high_error_rate(error_count: int, time_window: int):
        """Alert on high error rate"""
        AlertManager.send_alert(
            severity="warning",
            title="High Error Rate Detected",
            message=f"{error_count} errors in {time_window} seconds",
            details={"error_count": error_count, "time_window": time_window}
        )

    @staticmethod
    def alert_database_down():
        """Alert when database is down"""
        AlertManager.send_alert(
            severity="critical",
            title="Database Connection Lost",
            message="Unable to connect to the database",
            details={}
        )

    @staticmethod
    def alert_high_latency(endpoint: str, latency: float):
        """Alert on high latency"""
        AlertManager.send_alert(
            severity="warning",
            title="High Latency Detected",
            message=f"{endpoint} responding in {latency:.2f}s",
            details={"endpoint": endpoint, "latency": latency}
        )
