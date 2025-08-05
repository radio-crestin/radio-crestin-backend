"""
REST API endpoints for the GraphQL app

This module defines the actual REST endpoints for health checks and system status.
"""

from typing import Dict, Any
from django.db import connection
from django.core.cache import cache

from superapp.apps.graphql.rest_api import RestApiEndpoint, HttpMethod


class HealthCheckEndpoint(RestApiEndpoint):
    """
    Health check endpoint for monitoring services
    
    Returns a simple OK status to indicate the service is running.
    """
    
    path = "health"
    method = HttpMethod.GET
    name = "health_check"
    cache_control = "no-cache"
    cors_enabled = False  # Health checks usually don't need CORS
    
    # Simple GraphQL query to verify GraphQL is working
    graphql_query = """
    query HealthCheck {
        __typename
    }
    """
    
    @staticmethod
    def post_processor(response_data: Dict[str, Any], request, **kwargs) -> Dict[str, Any]:
        """Return health status"""
        return {
            "status": "ok",
            "service": "radio-crestin-backend"
        }


class ReadinessCheckEndpoint(RestApiEndpoint):
    """
    Readiness check endpoint that verifies all services are ready
    
    Checks database and cache connectivity.
    """
    
    path = "ready"
    method = HttpMethod.GET
    name = "readiness_check"
    cache_control = "no-cache"
    cors_enabled = False
    
    # GraphQL query to check if GraphQL is ready
    graphql_query = """
    query ReadinessCheck {
        __typename
    }
    """
    
    @staticmethod
    def post_processor(response_data: Dict[str, Any], request, **kwargs) -> Dict[str, Any]:
        """Check service readiness"""
        checks = {
            "database": False,
            "cache": False,
            "graphql": False
        }
        
        # Check database
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                checks["database"] = True
        except Exception:
            pass
        
        # Check cache
        try:
            cache.set("readiness_check", "ok", 1)
            if cache.get("readiness_check") == "ok":
                checks["cache"] = True
        except Exception:
            pass
        
        # Check GraphQL
        if 'data' in response_data and '__typename' in response_data.get('data', {}):
            checks["graphql"] = True
        
        # Determine overall status
        all_healthy = all(checks.values())
        
        return {
            "status": "ready" if all_healthy else "not_ready",
            "checks": checks
        }


# Register these endpoints
REST_ENDPOINTS = [
    HealthCheckEndpoint,
    ReadinessCheckEndpoint,
]