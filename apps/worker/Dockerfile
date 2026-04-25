FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt ./apps/api/requirements.txt
RUN pip install --no-cache-dir -r apps/api/requirements.txt

COPY apps/api ./apps/api
COPY apps/worker ./apps/worker
COPY packages ./packages

RUN adduser --disabled-password --gecos "" appuser
USER appuser

CMD ["python", "-m", "apps.worker.runtime"]
