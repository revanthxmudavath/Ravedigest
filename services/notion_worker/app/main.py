#services/notion_worker/app/main.py
from fastapi import FastAPI
import asyncio
from contextlib import asynccontextmanager
from services.notion_worker.app.worker import consume_digest_stream
from shared.config.settings import get_settings
from shared.logging.logger import setup_logging, get_logger
from shared.utils.health import create_notion_health_checker

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



