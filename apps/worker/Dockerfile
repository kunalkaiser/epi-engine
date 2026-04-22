FROM python:3.12-slim

WORKDIR /app

COPY apps/worker/requirements.txt ./apps/worker/requirements.txt
RUN pip install --no-cache-dir -r apps/worker/requirements.txt

COPY apps ./apps
