"""
Health check endpoints for production deployment.
"""

from fastapi import FastAPI, Response, status
from typing import Dict, Any
import time
import logging
import sys

logger = logging.getLogger(__name__)

app = FastAPI()

# Track startup time
STARTUP_TIME = time.time()


async def check_agentos_connection() -> bool:
    """Check connection to agentOS backend."""
    try:
        import os
        import httpx
        
        url = os.getenv("AGENTOS_URL", "http://localhost:5000")
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{url}/debug/status")
            return response.status_code == 200
    except Exception as e:
        logger.warning(f"AgentOS connection check failed: {e}")
        return False


async def check_redis_connection() -> bool:
    """Check connection to Redis (optional)."""
    try:
        import os
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            return True  # Not configured, skip check
        
        # Try to connect
        import redis.asyncio as redis
        client = redis.from_url(redis_url)
        await client.ping()
        await client.close()
        return True
    except Exception as e:
        logger.warning(f"Redis connection check failed: {e}")
        return False


async def check_database_connection() -> bool:
    """Check database connection (optional)."""
    try:
        import os
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            return True  # Not configured, skip check
        
        # Try to connect
        # Add your database check here
        return True
    except Exception as e:
        logger.warning(f"Database connection check failed: {e}")
        return False


@app.get("/health/live")
async def liveness() -> Dict[str, Any]:
    """
    Liveness probe - returns 200 if process is running.
    
    Used by Kubernetes to determine if container should be restarted.
    """
    return {
        "status": "alive",
        "timestamp": time.time(),
        "uptime": time.time() - STARTUP_TIME,
        "version": "0.1.0"
    }


@app.get("/health/ready")
async def readiness() -> Response:
    """
    Readiness probe - returns 200 if ready to serve traffic.
    
    Checks:
    - AgentOS connection
    - Redis connection (if configured)
    - Database connection (if configured)
    """
    checks = {
        "agentos": await check_agentos_connection(),
        "redis": await check_redis_connection(),
        "database": await check_database_connection(),
    }
    
    all_healthy = all(checks.values())
    
    response_data = {
        "status": "ready" if all_healthy else "not_ready",
        "timestamp": time.time(),
        "uptime": time.time() - STARTUP_TIME,
        "checks": checks
    }
    
    if all_healthy:
        return Response(
            content=str(response_data),
            status_code=status.HTTP_200_OK,
            media_type="application/json"
        )
    else:
        return Response(
            content=str(response_data),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json"
        )


@app.get("/health")
async def health() -> Dict[str, Any]:
    """
    Combined health check with detailed information.
    """
    checks = {
        "agentos": await check_agentos_connection(),
        "redis": await check_redis_connection(),
        "database": await check_database_connection(),
    }
    
    return {
        "status": "healthy" if all(checks.values()) else "degraded",
        "timestamp": time.time(),
        "uptime": time.time() - STARTUP_TIME,
        "version": "0.1.0",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "checks": checks
    }


@app.get("/metrics")
async def metrics() -> Response:
    """
    Prometheus-compatible metrics endpoint.
    
    Returns metrics in Prometheus exposition format.
    """
    # Collect metrics
    uptime = time.time() - STARTUP_TIME
    
    metrics_text = f"""# HELP agentosx_uptime_seconds Uptime in seconds
# TYPE agentosx_uptime_seconds gauge
agentosx_uptime_seconds {uptime}

# HELP agentosx_version_info Version information
# TYPE agentosx_version_info gauge
agentosx_version_info{{version="0.1.0"}} 1

# HELP agentosx_health_status Health status (1=healthy, 0=unhealthy)
# TYPE agentosx_health_status gauge
agentosx_health_status 1
"""
    
    return Response(
        content=metrics_text,
        media_type="text/plain"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)
