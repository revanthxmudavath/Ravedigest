FROM python:3.11-slim

WORKDIR /app

COPY services/collector/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/collector/src/collector ./collector
COPY shared ./shared

ENV PYTHONPATH=/app

CMD ["uvicorn", "collector.main:app", "--host", "0.0.0.0", "--port", "8001"]
