FROM python:3.12-slim

WORKDIR /app

COPY services/observability ./observability
COPY services/frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Frontend static prototype lives in the repo's frontend/ — bake it into the image.
COPY frontend ./static

COPY services/frontend/main.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
