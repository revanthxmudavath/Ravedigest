import schedule
import time
import requests
import os
from threading import Thread
from fastapi import FastAPI
import uvicorn
from tenacity import retry, stop_after_attempt, wait_fixed
from shared.app_logging.logger import setup_logging

# Setup logging
logger = setup_logging("scheduler")

# Get service URLs from environment variables
COLLECTOR_URL = os.getenv("COLLECTOR_URL", "http://collector:8001")
COMPOSER_URL = os.getenv("COMPOSER_URL", "http://composer:8003")
ANALYZER_URL = os.getenv("ANALYZER_URL", "http://analyzer:8002")
NOTION_WORKER_URL = os.getenv("NOTION_WORKER_URL", "http://notion-worker:8004")

@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def trigger_collector():
    """Trigger the collector service to start collecting articles."""
    url = f"{COLLECTOR_URL}/collect/rss"
    logger.info(f"Triggering collector service at {url}")
    response = requests.get(url)
    response.raise_for_status()
    logger.info("Collector service triggered successfully.")
    return response.json()

@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def trigger_composer():
    """Trigger the composer service to generate a digest."""
    url = f"{COMPOSER_URL}/compose"
    logger.info(f"Triggering composer service at {url}")
    response = requests.post(url)
    response.raise_for_status()
    logger.info("Composer service triggered successfully.")
    return response.json()

@retry(stop=stop_after_attempt(60), wait=wait_fixed(10))
def wait_for_service(service_name: str, url: str):
    """Wait for a service to become idle."""
    logger.info(f"Waiting for {service_name} to become idle...")
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    if not data.get("is_idle"):
        raise Exception(f"{service_name} is not idle yet.")
    logger.info(f"{service_name} is idle.")

def daily_job():
    """The job to be run daily."""
    logger.info("Starting daily job...")
    try:
        trigger_collector()
        wait_for_service("analyzer", f"{ANALYZER_URL}/analyzer/status")
        trigger_composer()
        wait_for_service("notion-worker", f"{NOTION_WORKER_URL}/notion/status")
        logger.info("Daily job completed successfully.")
    except Exception as e:
        logger.error(f"An error occurred during the daily job: {e}")

def run_schedule():
    """Run the scheduler."""
    # Schedule the job every day at 8:30 am
    schedule.every().day.at("08:30").do(daily_job)

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
    scheduler_thread = Thread(target=run_schedule)
    scheduler_thread.start()

    # Run the FastAPI app in the main thread
    run_fastapi()