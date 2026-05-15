FROM python:3.12-slim

WORKDIR /app

COPY services/observability ./observability
COPY services/agent/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY services/agent/agent.py \
     services/agent/approval_gate.py \
     services/agent/remediation.py \
     services/agent/server.py \
     ./
COPY services/agent/prompts ./prompts

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
