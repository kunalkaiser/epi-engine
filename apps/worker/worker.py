from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from apps.api.logging_utils import get_logger, log_event
from apps.api.platform_services import process_queued_simulation_jobs
from apps.worker.live_ingestion import run_live_ingestion


logger = get_logger("epi_engine.worker.runtime")

# Live ingestion runs at most once per this interval (env-configurable).
_LIVE_INGESTION_INTERVAL_HOURS: float = float(
    os.getenv("LIVE_INGESTION_INTERVAL_HOURS", "24")
)
_last_live_ingestion: datetime | None = None


@dataclass(frozen=True)
class WorkerSettings:
    app_env: str
    clickhouse_url: str
    loop_interval_seconds: int
    run_once: bool
    simulation_batch_size: int = 5
    heartbeat_file: str = "/tmp/epios-worker-heartbeat"


def load_worker_settings() -> WorkerSettings:
    settings = WorkerSettings(
        app_env=os.getenv("APP_ENV", "development"),
        clickhouse_url=os.getenv("CLICKHOUSE_URL", "http://localhost:8123"),
        loop_interval_seconds=max(int(os.getenv("WORKER_LOOP_INTERVAL_SECONDS", "60")), 5),
        run_once=os.getenv("WORKER_RUN_ONCE", "false").lower() == "true",
        simulation_batch_size=max(int(os.getenv("WORKER_SIMULATION_BATCH_SIZE", "5")), 1),
        heartbeat_file=os.getenv("WORKER_HEARTBEAT_FILE", "/tmp/epios-worker-heartbeat"),
    )
    _validate_worker_settings(settings)
    return settings


def run_worker_loop(settings: WorkerSettings | None = None) -> None:
    settings = settings or load_worker_settings()
    log_event(
        logger,
        logging.INFO,
        "worker.started",
        app_env=settings.app_env,
        loop_interval_seconds=settings.loop_interval_seconds,
        run_once=settings.run_once,
        simulation_batch_size=settings.simulation_batch_size,
    )
    while True:
        execute_scheduled_jobs(settings=settings)
        if settings.run_once:
            log_event(logger, logging.INFO, "worker.completed_single_run")
            return
        time.sleep(settings.loop_interval_seconds)


def execute_scheduled_jobs(*, settings: WorkerSettings | None = None) -> None:
    settings = settings or load_worker_settings()
    try:
        processed_runs = process_queued_simulation_jobs(max_runs=settings.simulation_batch_size)
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        log_event(logger, logging.ERROR, "worker.simulation_queue_failed", error_type=type(exc).__name__)
        processed_runs = 0

    _run_live_ingestion_if_due()

    log_event(
        logger,
        logging.INFO,
        "worker.job_tick",
        jobs=["ingestion_refresh", "score_recompute", "dq_checks", "simulation_queue", "live_ingestion"],
        processed_simulation_runs=processed_runs,
    )
    _write_heartbeat(settings.heartbeat_file)


def _run_live_ingestion_if_due() -> None:
    global _last_live_ingestion
    now = datetime.now(UTC)
    interval = timedelta(hours=_LIVE_INGESTION_INTERVAL_HOURS)
    if _last_live_ingestion is not None and (now - _last_live_ingestion) < interval:
        return

    log_event(logger, logging.INFO, "worker.live_ingestion.starting")
    try:
        results = run_live_ingestion()
        _last_live_ingestion = now
        ok = sum(1 for r in results if r["status"] == "ok")
        err = sum(1 for r in results if r["status"] == "error")
        total_rows = sum(r["rows_fetched"] for r in results)
        log_event(
            logger,
            logging.INFO,
            "worker.live_ingestion.completed",
            adapters_ok=ok,
            adapters_error=err,
            total_rows=total_rows,
        )
    except Exception as exc:
        log_event(logger, logging.ERROR, "worker.live_ingestion.failed", error_type=type(exc).__name__, error=str(exc))


def _validate_worker_settings(settings: WorkerSettings) -> None:
    if settings.app_env in {"staging", "production"}:
        if "localhost" in settings.clickhouse_url or "127.0.0.1" in settings.clickhouse_url:
            raise ValueError("CLICKHOUSE_URL must not point to localhost in staging/production worker")
        if settings.loop_interval_seconds > 600:
            raise ValueError("WORKER_LOOP_INTERVAL_SECONDS is too high for staging/production")


def _write_heartbeat(path: str) -> None:
    heartbeat_path = Path(path)
    heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
    heartbeat_path.write_text(str(int(time.time())), encoding="utf-8")


if __name__ == "__main__":
    run_worker_loop()
