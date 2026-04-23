from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib import error, parse, request
from uuid import uuid4

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
from apps.worker.source_adapters import get_source_adapter, supported_source_kinds


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


class IngestionRunStore(Protocol):
    def start_run(
        self,
        *,
        tenant_id: str,
        dataset_name: str,
        source_system: str,
        trigger_source: str,
        created_by: str,
        source_ref: str,
    ) -> str:
        ...

    def complete_run(
        self,
        *,
        run_id: str,
        tenant_id: str,
        records_processed: int,
        records_inserted: int,
        records_updated: int,
        records_rejected: int,
        validation_summary: dict[str, Any],
        error_summary: dict[str, Any],
        freshness_metric: str | None,
        provenance_ref: str | None,
        artifact_ref: str | None,
    ) -> None:
        ...

    def fail_run(self, *, run_id: str, tenant_id: str, error_summary: dict[str, Any]) -> None:
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


class ClickHouseIngestionRunStore:
    def __init__(self, base_url: str, database: str = "epi_engine") -> None:
        self.base_url = base_url.rstrip("/")
        self.database = database

    def start_run(
        self,
        *,
        tenant_id: str,
        dataset_name: str,
        source_system: str,
        trigger_source: str,
        created_by: str,
        source_ref: str,
    ) -> str:
        run_id = f"ing_{uuid4().hex}"
        now = datetime.now(UTC).isoformat()
        self._execute(
            f"""
            INSERT INTO {self.database}.ingestion_runs_v2
            (
                run_id, tenant_id, dataset_name, source_system, trigger_source, status, source_ref,
                records_processed, records_inserted, records_updated, records_rejected,
                validation_summary_json, error_summary_json, freshness_metric, provenance_ref, artifact_ref,
                created_by, started_at, completed_at, created_at, updated_at
            )
            VALUES
            (
                '{run_id}', '{tenant_id}', '{dataset_name}', '{source_system}', '{trigger_source}', 'running', '{source_ref}',
                0, 0, 0, 0,
                '{{}}', '{{}}', '', '', '',
                '{created_by}', parseDateTimeBestEffort('{now}'), NULL, parseDateTimeBestEffort('{now}'), parseDateTimeBestEffort('{now}')
            )
            """
        )
        return run_id

    def complete_run(
        self,
        *,
        run_id: str,
        tenant_id: str,
        records_processed: int,
        records_inserted: int,
        records_updated: int,
        records_rejected: int,
        validation_summary: dict[str, Any],
        error_summary: dict[str, Any],
        freshness_metric: str | None,
        provenance_ref: str | None,
        artifact_ref: str | None,
    ) -> None:
        current = self._latest_run(run_id=run_id, tenant_id=tenant_id)
        now = datetime.now(UTC).isoformat()
        self._execute(
            f"""
            INSERT INTO {self.database}.ingestion_runs_v2
            (
                run_id, tenant_id, dataset_name, source_system, trigger_source, status, source_ref,
                records_processed, records_inserted, records_updated, records_rejected,
                validation_summary_json, error_summary_json, freshness_metric, provenance_ref, artifact_ref,
                created_by, started_at, completed_at, created_at, updated_at
            )
            VALUES
            (
                '{run_id}', '{tenant_id}', '{current["dataset_name"]}', '{current["source_system"]}', '{current["trigger_source"]}', 'succeeded', '{current["source_ref"]}',
                {records_processed}, {records_inserted}, {records_updated}, {records_rejected},
                {json.dumps(json.dumps(validation_summary))}, {json.dumps(json.dumps(error_summary))},
                {json.dumps(freshness_metric or "")}, {json.dumps(provenance_ref or "")}, {json.dumps(artifact_ref or "")},
                '{current["created_by"]}',
                parseDateTimeBestEffort('{current["started_at"]}'),
                parseDateTimeBestEffort('{now}'),
                parseDateTimeBestEffort('{current["created_at"]}'),
                parseDateTimeBestEffort('{now}')
            )
            """
        )

    def fail_run(self, *, run_id: str, tenant_id: str, error_summary: dict[str, Any]) -> None:
        current = self._latest_run(run_id=run_id, tenant_id=tenant_id)
        now = datetime.now(UTC).isoformat()
        self._execute(
            f"""
            INSERT INTO {self.database}.ingestion_runs_v2
            (
                run_id, tenant_id, dataset_name, source_system, trigger_source, status, source_ref,
                records_processed, records_inserted, records_updated, records_rejected,
                validation_summary_json, error_summary_json, freshness_metric, provenance_ref, artifact_ref,
                created_by, started_at, completed_at, created_at, updated_at
            )
            VALUES
            (
                '{run_id}', '{tenant_id}', '{current["dataset_name"]}', '{current["source_system"]}', '{current["trigger_source"]}', 'failed', '{current["source_ref"]}',
                {int(current["records_processed"])}, {int(current["records_inserted"])}, {int(current["records_updated"])}, {int(current["records_rejected"])},
                {json.dumps(current["validation_summary_json"])}, {json.dumps(json.dumps(error_summary))},
                {json.dumps(current.get("freshness_metric", "") or "")},
                {json.dumps(current.get("provenance_ref", "") or "")},
                {json.dumps(current.get("artifact_ref", "") or "")},
                '{current["created_by"]}',
                parseDateTimeBestEffort('{current["started_at"]}'),
                parseDateTimeBestEffort('{now}'),
                parseDateTimeBestEffort('{current["created_at"]}'),
                parseDateTimeBestEffort('{now}')
            )
            """
        )

    def _latest_run(self, *, run_id: str, tenant_id: str) -> dict[str, Any]:
        query = (
            f"SELECT * FROM {self.database}.ingestion_runs_v2 "
            f"WHERE run_id={json.dumps(run_id)} AND tenant_id={json.dumps(tenant_id)} "
            "ORDER BY updated_at DESC LIMIT 1 FORMAT JSONEachRow"
        )
        endpoint = f"{self.base_url}/?{parse.urlencode({'query': query})}"
        http_request = request.Request(endpoint, method="POST")
        with request.urlopen(http_request) as response:
            body = response.read().decode("utf-8")
        rows = [json.loads(line) for line in body.splitlines() if line.strip()]
        if not rows:
            raise RuntimeError(f"ingestion run not found: {run_id}")
        return rows[0]

    def _execute(self, query: str) -> None:
        endpoint = f"{self.base_url}/?{parse.urlencode({'query': query})}"
        http_request = request.Request(endpoint, data=b"", method="POST")
        try:
            with request.urlopen(http_request) as response:
                response.read()
        except error.URLError as exc:
            raise RuntimeError("failed to persist ingestion run") from exc


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
    run_store: IngestionRunStore | None = None,
    tenant_id: str = "dev-tenant",
    source_system: str = "local_file",
    trigger_source: str = "manual",
    created_by: str = "system",
) -> IngestionResult:
    input_path = Path(input_path)
    if source_kind not in supported_source_kinds():
        raise ValueError(f"unsupported source_kind: {source_kind}")
    if not input_path.exists():
        raise FileNotFoundError(f"input file does not exist: {input_path}")

    dataset_config = DATASETS.get(dataset)
    if dataset_config is None:
        raise ValueError(f"unsupported dataset: {dataset}")

    log_event(logger, logging.INFO, "ingestion.started", dataset=dataset, input_path=str(input_path))
    source_load = get_source_adapter(source_kind).load(input_path)
    resolved_source_system = source_system if source_system != "local_file" else source_load.source_system
    run_id: str | None = None
    if run_store is not None:
        run_id = run_store.start_run(
            tenant_id=tenant_id,
            dataset_name=dataset,
            source_system=resolved_source_system,
            trigger_source=trigger_source,
            created_by=created_by,
            source_ref=str(input_path),
        )
    rows = source_load.rows
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

    try:
        staging_store.store_rows(dataset_config.staging_table, valid_rows)
    except Exception as exc:
        if run_store is not None and run_id is not None:
            run_store.fail_run(
                run_id=run_id,
                tenant_id=tenant_id,
                error_summary={"storage_error": str(exc)},
            )
        raise

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

    if run_store is not None and run_id is not None:
        run_store.complete_run(
            run_id=run_id,
            tenant_id=tenant_id,
            records_processed=summary.total_rows,
            records_inserted=summary.valid_rows,
            records_updated=0,
            records_rejected=summary.invalid_rows,
            validation_summary={"error_counts": summary.error_counts},
            error_summary={},
            freshness_metric=source_load.freshness_timestamp,
            provenance_ref=json.dumps(source_load.provenance, sort_keys=True),
            artifact_ref=str(report_path) if report_path is not None else None,
        )

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
