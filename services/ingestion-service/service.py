from __future__ import annotations

from pathlib import Path

from apps.worker.ingestion import IngestionResult, StagingStore, ingest_file


def run_ingestion(
    dataset: str,
    input_path: str | Path,
    staging_store: StagingStore,
    report_path: str | Path | None = None,
) -> IngestionResult:
    return ingest_file(
        dataset=dataset,
        input_path=input_path,
        source_kind="synthetic",
        staging_store=staging_store,
        report_path=report_path,
    )
