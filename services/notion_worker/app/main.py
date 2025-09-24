#services/notion_worker/app/main.py
from fastapi import FastAPI, HTTPException
import asyncio
import redis
from contextlib import asynccontextmanager
from services.notion_worker.app.worker import consume_digest_stream
from shared.config.settings import get_settings
from shared.app_logging.logger import setup_logging, get_logger
from shared.utils.health import create_notion_health_checker
from shared.utils.redis_client import get_redis_client

# Setup logging
logger = setup_logging("notion_worker")

# Get configuration
settings = get_settings()

# Create health checker
health_checker = create_notion_health_checker()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Notion Worker lifespan triggered")
    
    task = asyncio.create_task(consume_digest_stream())
    yield   
    task.cancel() 

app = FastAPI(lifespan=lifespan)


@app.get("/notion/health")
def health_check():
    """Comprehensive health check endpoint."""
    return health_checker.run_all_checks()

@app.get("/notion/health/live")
def liveness_check():
    """Liveness check endpoint."""
    return {"status": "alive", "service": "notion_worker"}

@app.get("/notion/health/ready")
def readiness_check():
    """Readiness check endpoint."""
    health_data = health_checker.run_all_checks()
    critical_checks = [check for check in health_data["checks"] 
                      if check["name"] in ["database", "redis", "notion"]]
    all_critical_healthy = all(check["status"] == "healthy" for check in critical_checks)
    
    return {
        "status": "ready" if all_critical_healthy else "not_ready",
        "service": "notion_worker",
        "critical_dependencies": {
            check["name"]: check["status"] for check in critical_checks
        }
    }


@app.get("/notion/status")
def get_notion_worker_status():
    """Check if the notion worker has processed all digests."""
    redis_client = get_redis_client("notion_worker_status")
    stream_name = "digests"
    group_name = f"{settings.service.consumer_group_prefix}-notion"

    try:
        # Get stream info
        stream_info = redis_client.xinfo_stream(stream_name)
        last_generated_id = stream_info.get("last-generated-id")

        # Get consumer group info
        groups = redis_client.xinfo_groups(stream_name)
        group_info = next((g for g in groups if g["name"] == group_name), None)

        if not group_info:
            raise HTTPException(status_code=404, detail=f"Consumer group {group_name} not found.")

        last_delivered_id = group_info.get("last-delivered-id")
        pending_messages = group_info.get("pending")

        is_idle = (last_generated_id == last_delivered_id) and (pending_messages == 0)

        return {
            "is_idle": is_idle,
            "last_generated_id": last_generated_id,
            "last_delivered_id": last_delivered_id,
            "pending_messages": pending_messages,
        }

    except redis.exceptions.ResponseError as e:
        # Handle case where the stream doesn't exist yet
        if "no such key" in str(e).lower():
            return {
                "is_idle": True,
                "status": "Stream not found, assuming idle."
            }
        logger.error(f"Redis error checking notion worker status: {e}")
        raise HTTPException(status_code=500, detail="Error checking notion worker status.")
    except Exception as e:
        logger.error(f"Unexpected error checking notion worker status: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

