FROM python:3.12-slim

WORKDIR /app

COPY services/notion_worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
EXPOSE 8004

HEALTHCHECK --interval=10s --timeout=5s CMD curl -f http://localhost:8004/notion/health || exit 1

CMD ["uvicorn", "services.notion_worker.app.main:app", "--host", "0.0.0.0", "--port", "8004"]
