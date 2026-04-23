from pathlib import Path
import os

import pytest

from apps.worker.worker import WorkerSettings, execute_scheduled_jobs, run_worker_loop


def setup_function() -> None:
    os.environ["APP_ENV"] = "development"
    os.environ["CLICKHOUSE_URL"] = "http://localhost:8123"


def test_worker_single_run_exits_cleanly() -> None:
    run_worker_loop(WorkerSettings(app_env="development", clickhouse_url="http://localhost:8123", loop_interval_seconds=5, run_once=True))


def test_worker_job_tick_executes_without_error() -> None:
    execute_scheduled_jobs()


def test_worker_tick_writes_heartbeat(tmp_path: Path) -> None:
    heartbeat_path = tmp_path / "worker-heartbeat"
    settings = WorkerSettings(
        app_env="development",
        clickhouse_url="http://localhost:8123",
        loop_interval_seconds=5,
        run_once=True,
        heartbeat_file=str(heartbeat_path),
    )
    execute_scheduled_jobs(settings=settings)
    assert heartbeat_path.exists()


def test_worker_rejects_localhost_clickhouse_in_production(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CLICKHOUSE_URL", "http://localhost:8123")
    with pytest.raises(ValueError):
        from apps.worker.worker import load_worker_settings

        load_worker_settings()
