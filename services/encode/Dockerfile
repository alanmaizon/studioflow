FROM python:3.12-slim

WORKDIR /app

COPY services/observability ./observability
COPY services/encode/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY services/encode .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]