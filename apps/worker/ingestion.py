from __future__ import annotations

import csv
import json
import logging
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib import error, parse, request

import pandas as pd
from pydantic import BaseModel, ValidationError

from apps.api.contracts import (
    Diagnosis,
    Encounter,
    IncidenceAggregate,
    IndicationScore,
    LabResult,
    Medication,
    PatientSummary,
    PrevalenceAggregate,
)
from apps.api.logging_utils import get_logger, log_event


logger = get_logger("epi_engine.worker.ingestion")


@dataclass(frozen=True)
class DatasetConfig:
    name: str
    model: type[BaseModel]
    staging_table: str


@dataclass(frozen=True)
class InvalidRow:
    row_number: int
    data: dict[str, Any]
    errors: list[str]


@dataclass(frozen=True)
class IngestionSummary:
    dataset: str
    source_kind: str
    input_path: str
    staging_table: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    error_counts: dict[str, int]
    generated_at: str


@dataclass(frozen=True)
class IngestionResult:
    summary: IngestionSummary
    valid_rows: list[dict[str, Any]]
    invalid_rows: list[InvalidRow]


class StagingStore(Protocol):
    def store_rows(self, table_name: str, rows: list[dict[str, Any]]) -> None:
        ...


class InMemoryStagingStore:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {}

    def store_rows(self, table_name: str, rows: list[dict[str, Any]]) -> None:
        existing_rows = self.tables.setdefault(table_name, [])
        existing_rows.extend(rows)


class ClickHouseStagingStore:
    def __init__(self, base_url: str, database: str = "epi_engine") -> None:
        self.base_url = base_url.rstrip("/")
        self.database = database

    def store_rows(self, table_name: str, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return

        query = f"INSERT INTO {self.database}.{table_name} FORMAT JSONEachRow"
        payload = "\n".join(json.dumps(row) for row in rows).encode("utf-8")
        endpoint = f"{self.base_url}/?{parse.urlencode({'query': query})}"
        http_request = request.Request(endpoint, data=payload, method="POST")
        try:
            with request.urlopen(http_request) as response:
                response.read()
        except error.URLError as exc:
            raise RuntimeError(f"failed to write rows to ClickHouse staging table {table_name}") from exc


DATASETS: dict[str, DatasetConfig] = {
    "patient_summary": DatasetConfig(
        name="patient_summary",
        model=PatientSummary,
        staging_table="staging_patient_summary",
    ),
    "diagnosis": DatasetConfig(
        name="diagnosis",
        model=Diagnosis,
        staging_table="staging_diagnosis",
    ),
    "medication": DatasetConfig(
        name="medication",
        model=Medication,
        staging_table="staging_medication",
    ),
    "lab_result": DatasetConfig(
        name="lab_result",
        model=LabResult,
        staging_table="staging_lab_result",
    ),
    "encounter": DatasetConfig(
        name="encounter",
        model=Encounter,
        staging_table="staging_encounter",
    ),
    "incidence_aggregate": DatasetConfig(
        name="incidence_aggregate",
        model=IncidenceAggregate,
        staging_table="staging_incidence_aggregate",
    ),
    "prevalence_aggregate": DatasetConfig(
        name="prevalence_aggregate",
        model=PrevalenceAggregate,
        staging_table="staging_prevalence_aggregate",
    ),
    "indication_score": DatasetConfig(
        name="indication_score",
        model=IndicationScore,
        staging_table="staging_indication_score",
    ),
}


def ingest_file(
    dataset: str,
    input_path: str | Path,
    source_kind: str,
    staging_store: StagingStore,
    report_path: str | Path | None = None,
) -> IngestionResult:
    input_path = Path(input_path)
    if source_kind != "synthetic":
        raise ValueError("ingestion only accepts synthetic data sources")
    if not input_path.exists():
        raise FileNotFoundError(f"input file does not exist: {input_path}")

    dataset_config = DATASETS.get(dataset)
    if dataset_config is None:
        raise ValueError(f"unsupported dataset: {dataset}")

    log_event(logger, logging.INFO, "ingestion.started", dataset=dataset, input_path=str(input_path))
    rows = _load_rows(input_path)
    valid_rows: list[dict[str, Any]] = []
    invalid_rows: list[InvalidRow] = []
    error_counter: Counter[str] = Counter()

    for row_number, row in enumerate(rows, start=1):
        normalized_row = _normalize_row(row)
        try:
            validated = dataset_config.model.model_validate(normalized_row)
        except ValidationError as exc:
            error_messages = [_format_error(error_item) for error_item in exc.errors(include_url=False)]
            error_counter.update(error_messages)
            invalid_rows.append(
                InvalidRow(
                    row_number=row_number,
                    data=normalized_row,
                    errors=error_messages,
                )
            )
            continue

        valid_rows.append(validated.model_dump(mode="json"))

    staging_store.store_rows(dataset_config.staging_table, valid_rows)

    summary = IngestionSummary(
        dataset=dataset_config.name,
        source_kind=source_kind,
        input_path=str(input_path),
        staging_table=dataset_config.staging_table,
        total_rows=len(rows),
        valid_rows=len(valid_rows),
        invalid_rows=len(invalid_rows),
        error_counts=dict(sorted(error_counter.items())),
        generated_at=datetime.now(UTC).isoformat(),
    )
    result = IngestionResult(summary=summary, valid_rows=valid_rows, invalid_rows=invalid_rows)

    if report_path is not None:
        write_summary_report(result, report_path)

    log_event(
        logger,
        logging.INFO,
        "ingestion.completed",
        dataset=dataset,
        total_rows=summary.total_rows,
        valid_rows=summary.valid_rows,
        invalid_rows=summary.invalid_rows,
    )
    return result


def write_summary_report(result: IngestionResult, report_path: str | Path) -> None:
    report = {
        "summary": asdict(result.summary),
        "invalid_rows": [asdict(item) for item in result.invalid_rows],
    }
    Path(report_path).write_text(json.dumps(report, indent=2), encoding="utf-8")


def _load_rows(input_path: Path) -> list[dict[str, Any]]:
    suffix = input_path.suffix.lower()
    if suffix == ".csv":
        return _read_csv(input_path)
    if suffix == ".parquet":
        return _read_parquet(input_path)
    raise ValueError(f"unsupported file type: {suffix or 'unknown'}")


def _read_csv(input_path: Path) -> list[dict[str, Any]]:
    try:
        with input_path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    except OSError as exc:
        raise RuntimeError(f"failed to read csv input: {input_path}") from exc


def _read_parquet(input_path: Path) -> list[dict[str, Any]]:
    try:
        frame = pd.read_parquet(input_path)
    except (ImportError, ValueError) as exc:
        raise RuntimeError("parquet ingestion requires pandas with a parquet engine such as pyarrow") from exc
    return frame.to_dict(orient="records")


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _normalize_value(value) for key, value in row.items()}


def _normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if pd.isna(value):
        return None
    return value


def _format_error(error_item: dict[str, Any]) -> str:
    location = ".".join(str(part) for part in error_item["loc"])
    return f"{location}: {error_item['msg']}"
