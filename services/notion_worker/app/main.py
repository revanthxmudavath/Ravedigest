from fastapi import FastAPI
from services.notion_worker.app.publisher import publish_latest_digest

app = FastAPI()

@app.get("/notion/health")
def health_check():
    return {"status" : "ok"}

@app.post("/notion/publish-latest")
def trigger_publish():
    result = publish_latest_digest()
    return {"status" : "done", "notion_page_url": result}


