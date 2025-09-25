FROM python:3.12-slim

WORKDIR /app

COPY services/scheduler/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/scheduler/src/main.py .
COPY shared ./shared

ENV PYTHONPATH=/app

CMD ["python", "main.py"]