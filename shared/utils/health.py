"""
Health check utilities for RaveDigest services.
Provides comprehensive health monitoring and status reporting.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import text

from shared.app_logging.logger import get_logger
from shared.config.settings import get_settings
from shared.utils.redis_client import get_redis_client

logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result."""

    name: str
    status: HealthStatus
    message: str
    response_time_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class HealthChecker:
    """Comprehensive health checker for services."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = get_logger(f"{service_name}.health")
        self.checks: List[Callable[[], HealthCheck]] = []
        self.settings = get_settings()

    def add_check(self, check_func: Callable[[], HealthCheck]):
        """Add a health check function."""
        self.checks.append(check_func)

    def check_database(self) -> HealthCheck:
        """Check database connectivity."""
        start_time = datetime.now()
        try:
            from shared.database.session import SessionLocal

            with SessionLocal() as session:
                session.execute(text("SELECT 1"))

            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return HealthCheck(
                name="database",
                status=HealthStatus.HEALTHY,
                message="Database connection successful",
                response_time_ms=response_time,
            )
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return HealthCheck(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
                response_time_ms=response_time,
            )

    def check_redis(self) -> HealthCheck:
        """Check Redis connectivity."""
        start_time = datetime.now()
        try:
            redis_client = get_redis_client(self.service_name)
            redis_client.ping()

            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return HealthCheck(
                name="redis",
                status=HealthStatus.HEALTHY,
                message="Redis connection successful",
                response_time_ms=response_time,
            )
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return HealthCheck(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis connection failed: {str(e)}",
                response_time_ms=response_time,
            )

    def check_openai(self) -> HealthCheck:
        """Check OpenAI API connectivity."""
        start_time = datetime.now()
        try:
            import openai

            client = openai.OpenAI(api_key=self.settings.openai.api_key)
            # Simple API call to test connectivity
            client.models.list()

            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return HealthCheck(
                name="openai",
                status=HealthStatus.HEALTHY,
                message="OpenAI API connection successful",
                response_time_ms=response_time,
            )
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return HealthCheck(
                name="openai",
                status=HealthStatus.UNHEALTHY,
                message=f"OpenAI API connection failed: {str(e)}",
                response_time_ms=response_time,
            )

    def check_notion(self) -> HealthCheck:
        """Check Notion API connectivity."""
        start_time = datetime.now()
        try:
            from notion_client import Client

            client = Client(auth=self.settings.notion.api_key)
            # Simple API call to test connectivity
            client.users.me()

            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return HealthCheck(
                name="notion",
                status=HealthStatus.HEALTHY,
                message="Notion API connection successful",
                response_time_ms=response_time,
            )
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return HealthCheck(
                name="notion",
                status=HealthStatus.UNHEALTHY,
                message=f"Notion API connection failed: {str(e)}",
                response_time_ms=response_time,
            )

    def check_http_endpoint(self, url: str, name: str = "http_endpoint") -> HealthCheck:
        """Check HTTP endpoint connectivity."""
        start_time = datetime.now()
        try:
            import httpx

            with httpx.Client(timeout=5.0) as client:
                response = client.get(url)
                response.raise_for_status()

            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return HealthCheck(
                name=name,
                status=HealthStatus.HEALTHY,
                message=f"HTTP endpoint {url} is accessible",
                response_time_ms=response_time,
            )
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"HTTP endpoint {url} failed: {str(e)}",
                response_time_ms=response_time,
            )

    def run_all_checks(self) -> Dict[str, Any]:
        """Run all registered health checks."""
        results = []
        overall_status = HealthStatus.HEALTHY

        for check_func in self.checks:
            try:
                result = check_func()
                results.append(result)

                # Update overall status
                if result.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif (
                    result.status == HealthStatus.DEGRADED
                    and overall_status == HealthStatus.HEALTHY
                ):
                    overall_status = HealthStatus.DEGRADED

            except Exception as e:
                error_result = HealthCheck(
                    name=check_func.__name__,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check failed with exception: {str(e)}",
                )
                results.append(error_result)
                overall_status = HealthStatus.UNHEALTHY

        return {
            "service": self.service_name,
            "status": overall_status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": [
                {
                    "name": check.name,
                    "status": check.status.value,
                    "message": check.message,
                    "response_time_ms": check.response_time_ms,
                    "details": check.details,
                    "timestamp": check.timestamp.isoformat(),
                }
                for check in results
            ],
        }

    def get_health_summary(self) -> Dict[str, Any]:
        """Get a summary of health status."""
        health_data = self.run_all_checks()

        healthy_checks = sum(
            1 for check in health_data["checks"] if check["status"] == "healthy"
        )
        total_checks = len(health_data["checks"])

        return {
            "service": self.service_name,
            "status": health_data["status"],
            "healthy_checks": healthy_checks,
            "total_checks": total_checks,
            "health_percentage": (
                (healthy_checks / total_checks * 100) if total_checks > 0 else 0
            ),
            "timestamp": health_data["timestamp"],
        }


def create_health_checker(service_name: str) -> HealthChecker:
    """Create a health checker for a service with common checks."""
    checker = HealthChecker(service_name)

    # Add common checks
    checker.add_check(checker.check_database)
    checker.add_check(checker.check_redis)

    return checker


def create_analyzer_health_checker() -> HealthChecker:
    """Create health checker for analyzer service."""
    checker = create_health_checker("analyzer")
    checker.add_check(checker.check_openai)
    return checker


def create_notion_health_checker() -> HealthChecker:
    """Create health checker for notion worker service."""
    checker = create_health_checker("notion_worker")
    checker.add_check(checker.check_notion)
    return checker


def create_collector_health_checker() -> HealthChecker:
    """Create health checker for collector service."""
    checker = create_health_checker("collector")
    # Add RSS feed checks
    settings = get_settings()
    for i, feed_url in enumerate(settings.service.rss_feeds[:3]):  # Check first 3 feeds
        checker.add_check(
            lambda url=feed_url, idx=i: checker.check_http_endpoint(
                url, f"rss_feed_{idx}"
            )
        )
    return checker


def create_composer_health_checker() -> HealthChecker:
    """Create health checker for composer service."""
    return create_health_checker("composer")


# Health check decorators
def health_check_endpoint(checker: HealthChecker):
    """Decorator to create a health check endpoint."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            health_data = checker.run_all_checks()
            return health_data

        return wrapper

    return decorator


def liveness_check(checker: HealthChecker):
    """Decorator to create a liveness check endpoint."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Simple liveness check - just check if service is running
            return {
                "status": "alive",
                "service": checker.service_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        return wrapper

    return decorator


def readiness_check(checker: HealthChecker):
    """Decorator to create a readiness check endpoint."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Readiness check - check critical dependencies
            health_data = checker.run_all_checks()
            critical_checks = [
                check
                for check in health_data["checks"]
                if check["name"] in ["database", "redis"]
            ]

            all_critical_healthy = all(
                check["status"] == "healthy" for check in critical_checks
            )

            return {
                "status": "ready" if all_critical_healthy else "not_ready",
                "service": checker.service_name,
                "critical_dependencies": {
                    check["name"]: check["status"] for check in critical_checks
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        return wrapper

    return decorator
