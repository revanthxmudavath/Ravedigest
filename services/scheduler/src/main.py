import os
import time
from threading import Thread

import requests
import schedule
import uvicorn
from fastapi import FastAPI
from tenacity import RetryError, retry, stop_after_attempt, wait_fixed

from shared.app_logging.logger import setup_logging

# Setup logging
logger = setup_logging("scheduler")

# Get service URLs from environment variables
COLLECTOR_URL = os.getenv("COLLECTOR_URL", "http://collector:8001")
COMPOSER_URL = os.getenv("COMPOSER_URL", "http://composer:8003")
ANALYZER_URL = os.getenv("ANALYZER_URL", "http://analyzer:8002")
NOTION_WORKER_URL = os.getenv("NOTION_WORKER_URL", "http://notion-worker:8004")


REQUEST_TIMEOUT = float(os.getenv('SCHEDULER_HTTP_TIMEOUT', '30'))
STATUS_TIMEOUT = float(os.getenv('SCHEDULER_STATUS_TIMEOUT', '15'))
STATUS_MAX_ATTEMPTS = int(os.getenv('SCHEDULER_STATUS_MAX_ATTEMPTS', '35'))

@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def trigger_collector():
    """Trigger the collector service to start collecting articles."""
    url = f"{COLLECTOR_URL}/collect/rss"
    logger.info(f"Triggering collector service at {url}")
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    logger.info("Collector service triggered successfully.")
    return response.json()

@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def trigger_composer():
    """Trigger the composer service to generate a digest."""
    url = f"{COMPOSER_URL}/compose"
    logger.info(f"Triggering composer service at {url}")
    response = requests.post(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    logger.info("Composer service triggered successfully.")
    return response.json()

@retry(stop=stop_after_attempt(STATUS_MAX_ATTEMPTS), wait=wait_fixed(10))
def wait_for_service(service_name: str, url: str):
    """Wait for a service to become idle."""
    logger.info(f"Waiting for {service_name} to become idle...")

    try:
        response = requests.get(url, timeout=STATUS_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if not data.get("is_idle"):
            # Check if there's a status message about stream not existing
            status_msg = data.get("status", "")
            if "Stream not found" in status_msg:
                logger.info(f"{service_name} stream not found - assuming idle (no work to process)")
                return
            else:
                raise Exception(f"{service_name} is not idle yet. {status_msg}")

        logger.info(f"{service_name} is idle.")

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to check {service_name} status: {e}")
        raise Exception(f"Cannot reach {service_name} status endpoint: {e}")
    except Exception as e:
        logger.error(f"Error checking {service_name} status: {e}")
        raise

def daily_job():
    """The job to be run daily."""
    logger.info("Starting daily job...")

    try:
        trigger_collector()
    except Exception:
        logger.exception("Failed to trigger collector service")
        return

    try:
        wait_for_service("analyzer", f"{ANALYZER_URL}/analyzer/status")
    except RetryError:
        logger.warning("Analyzer did not become idle after %s attempts; deferring to next schedule", STATUS_MAX_ATTEMPTS)
        return
    except Exception:
        logger.exception("Error while waiting for analyzer to become idle")
        return

    try:
        trigger_composer()
    except Exception:
        logger.exception("Failed to trigger composer service")
        return

    try:
        wait_for_service("notion-worker", f"{NOTION_WORKER_URL}/notion/status")
    except RetryError:
        logger.warning("Notion worker did not become idle after %s attempts; deferring to next schedule", STATUS_MAX_ATTEMPTS)
        return
    except Exception:
        logger.exception("Error while waiting for notion worker to become idle")
        return

    logger.info("Daily job completed successfully.")

def run_schedule():
    """Run the scheduler."""
    # Schedule the job every day at 8:30 am
    schedule.every().day.at("14:25").do(daily_job)   #"08:30"

    while True:
        schedule.run_pending()
        time.sleep(1)

# FastAPI app for health checks
app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}

def run_fastapi():
    """Run the FastAPI app."""
    uvicorn.run(app, host="0.0.0.0", port=8005)

if __name__ == "__main__":
    # Run the scheduler in a separate thread
    scheduler_thread = Thread(target=run_schedule, daemon=True)
    scheduler_thread.start()

    # Run the FastAPI app in the main thread
    run_fastapi()
