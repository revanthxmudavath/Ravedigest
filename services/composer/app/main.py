import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import Depends, FastAPI, HTTPException, Response, status

from services.composer.app.digest_utils import generate_and_publish_digest, get_db
from services.composer.app.schema import DigestOut
from shared.app_logging.logger import get_logger, setup_logging
from shared.config.settings import get_settings
from shared.database.session import init_db
from shared.utils.health import create_composer_health_checker

# Setup logging
logger = setup_logging("composer")

# Get configuration
settings = get_settings()

# Create health checker
health_checker = create_composer_health_checker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from services.composer.app.worker import consume_enriched

    init_db()
    task = asyncio.create_task(consume_enriched())
    logger.info("Launched enriched_articles consumer")
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        logger.info("Composer consumer shut down cleanly")

        # Cleanup Redis connections
        from shared.utils.redis_client import close_all_redis_clients

        close_all_redis_clients()
        logger.info("Redis connections closed")


app = FastAPI(lifespan=lifespan)


@app.get("/compose/health")
def health():
    """Comprehensive health check endpoint."""
    return health_checker.run_all_checks()


@app.get("/compose/health/live")
def liveness_check():
    """Liveness check endpoint."""
    return {"status": "alive", "service": "composer"}


@app.get("/compose/health/ready")
def readiness_check():
    """Readiness check endpoint."""
    health_data = health_checker.run_all_checks()
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
        "service": "composer",
        "critical_dependencies": {
            check["name"]: check["status"] for check in critical_checks
        },
    }


@app.post("/compose", response_model=DigestOut)
def compose(response: Response, db=Depends(get_db)):
    """Generate and publish a digest."""
    try:
        logger.info("Starting digest composition")
        digest = generate_and_publish_digest(db)
        if digest is None:
            logger.info("No articles available; skipping digest generation")
            response.status_code = status.HTTP_204_NO_CONTENT
            return None
        logger.info(f"Successfully composed digest: {digest.id}")
        return DigestOut.model_validate(digest, from_attributes=True)
    except Exception as e:
        logger.exception("Unexpected error in /compose: %s", e)
        raise HTTPException(500, "Internal Server Error")
