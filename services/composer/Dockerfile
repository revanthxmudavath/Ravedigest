FROM python:3.12-slim

WORKDIR /app

COPY services/composer/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY . .

ENV PYTHONPATH=/app
EXPOSE 8003

HEALTHCHECK --interval=10s --timeout=5s CMD curl -f http://localhost:8003/compose/health || exit 1

CMD ["uvicorn", "services.composer.app.main:app", "--host", "0.0.0.0", "--port", "8003"]
