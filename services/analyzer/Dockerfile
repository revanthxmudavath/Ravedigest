FROM python:3.12-slim
WORKDIR /app

COPY services/analyzer/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV PYTHONPATH=/app

EXPOSE 8002
HEALTHCHECK --interval=30s --timeout=5s \
  CMD curl --fail http://localhost:8002/analyzer/health || exit 1

CMD ["uvicorn", "services.analyzer.main:app", "--host", "0.0.0.0", "--port", "8002"]
