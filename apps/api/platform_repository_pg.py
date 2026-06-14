from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from apps.api.platform_models import (
    DataQualityUpsertRequest,
    DataQualityResultStatus,
    IngestionRunStatusSummary,
    MethodologyMetadata,
    SimulationResultItem,
    SimulationRunSummary,
)
from apps.api.query_models import DataQualityRunsFilters, IngestionRunsFilters, SimulationRunsFilters
from apps.api.response_models import PaginationMeta
from apps.api.platform_repository import (
    PlatformPersistenceRepository,
    SimulationRunRecord,
    _build_pagination,
    _data_quality_from_row,
    _ingestion_summary_from_row,
    _simulation_summary_from_row,
)
from apps.api.pg import PostgresClient


class PostgresPlatformRepository(PlatformPersistenceRepository):
    """Postgres/Supabase port of the platform write path (Phase 2).

    Overrides only the SQL-bearing methods; ``compare_simulation_runs`` and
    ``cancel_simulation_run`` are inherited from the base and work unchanged
    because they call ``self.get_simulation_run`` / ``self.update_simulation_run``
    polymorphically.

    Unlike the ClickHouse ReplacingMergeTree model, ``simulation_runs`` is a
    mutable single row per (tenant_id, run_id): create = INSERT, status changes =
    UPDATE in place. Latest-state reads therefore need no anyLast/GROUP BY. The
    full transition history is still kept in ``simulation_run_events``.
    {name:Type} placeholders are translated to %(name)s by PostgresClient;
    ClickHouse ``parseDateTimeBestEffort(x)`` becomes ``x::timestamptz``.
    """

    def __init__(self, client: PostgresClient) -> None:
        self.client = client

    # ── simulation runs ──────────────────────────────────────────────────────
    def create_simulation_run(
        self,
        *,
        tenant_id: str,
        created_by: str,
        scenario_type: str,
        region: str | None,
        trigger_source: str,
        assumptions: dict[str, Any],
        methodology: MethodologyMetadata,
    ) -> str:
        run_id = f"sim_{uuid4().hex}"
        now = datetime.utcnow().isoformat()
        max_attempts = int(assumptions.get("max_attempts", 2))
        self.client.query_json(
            """
            INSERT INTO simulation_runs
            (run_id, tenant_id, status, scenario_type, region_code, created_by, trigger_source,
             assumptions_json, methodology_json, attempt_count, max_attempts, created_at, updated_at)
            VALUES
            ({run_id:String}, {tenant_id:String}, 'queued', {scenario_type:String}, {region_code:String},
             {created_by:String}, {trigger_source:String}, {assumptions_json:String}, {methodology_json:String},
             0, {max_attempts:UInt8}, {created_at:String}::timestamptz, {updated_at:String}::timestamptz)
            """,
            {
                "run_id": run_id,
                "tenant_id": tenant_id,
                "scenario_type": scenario_type,
                "region_code": region or "",
                "created_by": created_by,
                "trigger_source": trigger_source,
                "assumptions_json": json.dumps(assumptions, sort_keys=True),
                "methodology_json": methodology.model_dump_json(),
                "max_attempts": max_attempts,
                "created_at": now,
                "updated_at": now,
            },
        )
        self.append_simulation_event(
            run_id=run_id,
            tenant_id=tenant_id,
            event_type="queued",
            detail={"scenario_type": scenario_type, "created_by": created_by},
        )
        return run_id

    def update_simulation_run(
        self,
        *,
        run_id: str,
        tenant_id: str,
        status: str,
        result_summary: str | None = None,
        artifact_ref: str | None = None,
        error_message: str | None = None,
        attempt_count: int | None = None,
    ) -> None:
        current = self.get_simulation_run(run_id=run_id, tenant_id=tenant_id)
        if current is None:
            raise LookupError(f"simulation run not found: {run_id}")
        now = datetime.utcnow().isoformat()
        self.client.query_json(
            """
            UPDATE simulation_runs SET
                status = {status:String},
                result_summary = {result_summary:String},
                artifact_ref = {artifact_ref:String},
                error_message = {error_message:String},
                attempt_count = {attempt_count:UInt8},
                updated_at = {updated_at:String}::timestamptz
            WHERE run_id = {run_id:String} AND tenant_id = {tenant_id:String}
            """,
            {
                "run_id": run_id,
                "tenant_id": tenant_id,
                "status": status,
                "result_summary": result_summary or current.summary.result_summary or "",
                "artifact_ref": artifact_ref or current.summary.artifact_ref or "",
                "error_message": error_message or current.summary.error_message or "",
                "attempt_count": attempt_count if attempt_count is not None else current.summary.attempt_count,
                "updated_at": now,
            },
        )
        self.append_simulation_event(
            run_id=run_id,
            tenant_id=tenant_id,
            event_type=status,
            detail={"error": error_message or "", "summary": result_summary or ""},
        )

    def save_simulation_result_items(self, *, run_id: str, tenant_id: str, items: list[SimulationResultItem]) -> None:
        # Idempotent on re-run/retry: replace this run's items rather than append.
        self.client.query_json(
            "DELETE FROM simulation_run_items WHERE run_id = {run_id:String} AND tenant_id = {tenant_id:String}",
            {"run_id": run_id, "tenant_id": tenant_id},
        )
        for item in items:
            self.client.query_json(
                """
                INSERT INTO simulation_run_items
                (run_id, tenant_id, indication_id, indication_name, baseline_score, simulated_score,
                 score_delta, uncertainty_low, uncertainty_high, outcome_drivers_json, score_inputs_json, trace_id)
                VALUES
                ({run_id:String}, {tenant_id:String}, {indication_id:String}, {indication_name:String},
                 {baseline_score:Float64}, {simulated_score:Float64}, {score_delta:Float64},
                 {uncertainty_low:Float64}, {uncertainty_high:Float64}, {outcome_drivers_json:String},
                 {score_inputs_json:String}, {trace_id:String})
                """,
                {
                    "run_id": run_id,
                    "tenant_id": tenant_id,
                    "indication_id": item.indication_id,
                    "indication_name": item.indication_name,
                    "baseline_score": item.baseline_score,
                    "simulated_score": item.simulated_score,
                    "score_delta": item.score_delta,
                    "uncertainty_low": item.uncertainty_low,
                    "uncertainty_high": item.uncertainty_high,
                    "outcome_drivers_json": json.dumps(item.outcome_drivers),
                    "score_inputs_json": json.dumps(item.score_inputs, sort_keys=True),
                    "trace_id": item.trace_id,
                },
            )

    def get_simulation_run(self, *, run_id: str, tenant_id: str) -> SimulationRunRecord | None:
        rows = self.client.query_json(
            """
            SELECT run_id, tenant_id, status, scenario_type, region_code, created_by, trigger_source,
                   assumptions_json, methodology_json, result_summary, artifact_ref, error_message,
                   attempt_count, max_attempts, created_at, updated_at
            FROM simulation_runs
            WHERE run_id = {run_id:String} AND tenant_id = {tenant_id:String}
            """,
            {"run_id": run_id, "tenant_id": tenant_id},
        )
        if not rows:
            return None
        row = rows[0]
        item_rows = self.client.query_json(
            """
            SELECT indication_id, indication_name, baseline_score, simulated_score, score_delta,
                   uncertainty_low, uncertainty_high, outcome_drivers_json, score_inputs_json, trace_id
            FROM simulation_run_items
            WHERE run_id = {run_id:String} AND tenant_id = {tenant_id:String}
            ORDER BY indication_name ASC
            """,
            {"run_id": run_id, "tenant_id": tenant_id},
        )
        items = [
            SimulationResultItem(
                indication_id=item["indication_id"],
                indication_name=item["indication_name"],
                baseline_score=float(item["baseline_score"]),
                simulated_score=float(item["simulated_score"]),
                score_delta=float(item["score_delta"]),
                uncertainty_low=float(item.get("uncertainty_low", item["simulated_score"])),
                uncertainty_high=float(item.get("uncertainty_high", item["simulated_score"])),
                outcome_drivers=json.loads(item.get("outcome_drivers_json", "[]")),
                score_inputs=json.loads(item.get("score_inputs_json", "{}")),
                trace_id=item.get("trace_id", f"trace_{item['indication_id']}"),
            )
            for item in item_rows
        ]
        summary = _simulation_summary_from_row(row)
        return SimulationRunRecord(summary=summary, assumptions=json.loads(row["assumptions_json"]), items=items)

    def list_simulation_runs(
        self, *, tenant_id: str, filters: SimulationRunsFilters
    ) -> tuple[list[SimulationRunSummary], PaginationMeta]:
        where_parts = ["tenant_id = {tenant_id:String}"]
        params: dict[str, Any] = {"tenant_id": tenant_id}
        if filters.status:
            where_parts.append("status = {status:String}")
            params["status"] = filters.status
        if filters.scenario_type:
            where_parts.append("scenario_type = {scenario_type:String}")
            params["scenario_type"] = filters.scenario_type
        where_clause = f"WHERE {' AND '.join(where_parts)}"
        count_rows = self.client.query_json(
            f"SELECT count(*) AS total_items FROM simulation_runs {where_clause}",
            params,
        )
        total_items = int(count_rows[0]["total_items"]) if count_rows else 0
        offset = (filters.page - 1) * filters.page_size
        rows = self.client.query_json(
            f"""
            SELECT run_id, tenant_id, status, scenario_type, region_code, created_by, trigger_source,
                   methodology_json, result_summary, artifact_ref, error_message, attempt_count, max_attempts,
                   created_at, updated_at
            FROM simulation_runs
            {where_clause}
            ORDER BY updated_at DESC
            LIMIT {{limit:UInt64}} OFFSET {{offset:UInt64}}
            """,
            {**params, "limit": filters.page_size, "offset": offset},
        )
        summaries = [_simulation_summary_from_row(row) for row in rows]
        return summaries, _build_pagination(filters.page, filters.page_size, total_items)

    def list_runnable_simulation_runs(self, *, limit: int = 10) -> list[SimulationRunRecord]:
        rows = self.client.query_json(
            """
            SELECT run_id, tenant_id
            FROM simulation_runs
            WHERE status = 'queued'
            ORDER BY created_at ASC
            LIMIT {limit:UInt64}
            """,
            {"limit": limit},
        )
        records: list[SimulationRunRecord] = []
        for row in rows:
            record = self.get_simulation_run(run_id=row["run_id"], tenant_id=row["tenant_id"])
            if record is not None:
                records.append(record)
        return records

    def append_simulation_event(self, *, run_id: str, tenant_id: str, event_type: str, detail: dict[str, Any]) -> None:
        self.client.query_json(
            """
            INSERT INTO simulation_run_events
            (event_id, run_id, tenant_id, event_type, detail_json, created_at)
            VALUES
            ({event_id:String}, {run_id:String}, {tenant_id:String}, {event_type:String}, {detail_json:String}, now())
            """,
            {
                "event_id": f"sev_{uuid4().hex}",
                "run_id": run_id,
                "tenant_id": tenant_id,
                "event_type": event_type,
                "detail_json": json.dumps(detail, sort_keys=True),
            },
        )

    # ── ingestion runs (worker-written; read with DISTINCT ON latest) ─────────
    def list_ingestion_runs(
        self, *, tenant_id: str, filters: IngestionRunsFilters
    ) -> tuple[list[IngestionRunStatusSummary], PaginationMeta]:
        where_parts = ["tenant_id = {tenant_id:String}"]
        params: dict[str, Any] = {"tenant_id": tenant_id}
        if filters.source_system:
            where_parts.append("source_system = {source_system:String}")
            params["source_system"] = filters.source_system
        if filters.status:
            where_parts.append("status = {status:String}")
            params["status"] = filters.status
        if filters.trigger_source:
            where_parts.append("trigger_source = {trigger_source:String}")
            params["trigger_source"] = filters.trigger_source
        if filters.date_from:
            where_parts.append("started_at >= {date_from:String}::timestamptz")
            params["date_from"] = f"{filters.date_from.isoformat()}T00:00:00"
        if filters.date_to:
            where_parts.append("started_at <= {date_to:String}::timestamptz")
            params["date_to"] = f"{filters.date_to.isoformat()}T23:59:59"
        where_clause = f"WHERE {' AND '.join(where_parts)}"
        count_rows = self.client.query_json(
            f"SELECT count(DISTINCT run_id) AS total_items FROM ingestion_runs_v2 {where_clause}",
            params,
        )
        total_items = int(count_rows[0]["total_items"]) if count_rows else 0
        offset = (filters.page - 1) * filters.page_size
        rows = self.client.query_json(
            f"""
            SELECT * FROM (
                SELECT DISTINCT ON (run_id)
                    run_id, tenant_id, dataset_name, source_system, trigger_source, status,
                    records_processed, records_inserted, records_updated, records_rejected,
                    validation_summary_json, error_summary_json, freshness_metric, provenance_ref,
                    artifact_ref, created_by, started_at, completed_at, created_at, updated_at
                FROM ingestion_runs_v2
                {where_clause}
                ORDER BY run_id, updated_at DESC
            ) latest
            ORDER BY updated_at DESC
            LIMIT {{limit:UInt64}} OFFSET {{offset:UInt64}}
            """,
            {**params, "limit": filters.page_size, "offset": offset},
        )
        items = [_ingestion_summary_from_row(row) for row in rows]
        return items, _build_pagination(filters.page, filters.page_size, total_items)

    def get_ingestion_run(self, *, run_id: str, tenant_id: str) -> IngestionRunStatusSummary | None:
        rows = self.client.query_json(
            """
            SELECT run_id, tenant_id, dataset_name, source_system, trigger_source, status,
                   records_processed, records_inserted, records_updated, records_rejected,
                   validation_summary_json, error_summary_json, freshness_metric, provenance_ref,
                   artifact_ref, created_by, started_at, completed_at, created_at, updated_at
            FROM ingestion_runs_v2
            WHERE run_id = {run_id:String} AND tenant_id = {tenant_id:String}
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            {"run_id": run_id, "tenant_id": tenant_id},
        )
        if not rows:
            return None
        return _ingestion_summary_from_row(rows[0])

    # ── data quality results (append-only; distinct result_id) ────────────────
    def list_data_quality_results(
        self, *, tenant_id: str, filters: DataQualityRunsFilters
    ) -> tuple[list[DataQualityResultStatus], PaginationMeta]:
        where_parts = ["tenant_id = {tenant_id:String}"]
        params: dict[str, Any] = {"tenant_id": tenant_id}
        if filters.domain:
            where_parts.append("domain = {domain:String}")
            params["domain"] = filters.domain
        if filters.status:
            where_parts.append("status = {status:String}")
            params["status"] = filters.status
        if filters.severity:
            where_parts.append("severity = {severity:String}")
            params["severity"] = filters.severity
        if filters.date_from:
            where_parts.append("measured_at >= {date_from:String}::timestamptz")
            params["date_from"] = f"{filters.date_from.isoformat()}T00:00:00"
        if filters.date_to:
            where_parts.append("measured_at <= {date_to:String}::timestamptz")
            params["date_to"] = f"{filters.date_to.isoformat()}T23:59:59"
        where_clause = f"WHERE {' AND '.join(where_parts)}"
        count_rows = self.client.query_json(
            f"SELECT count(DISTINCT result_id) AS total_items FROM data_quality_results_v2 {where_clause}",
            params,
        )
        total_items = int(count_rows[0]["total_items"]) if count_rows else 0
        offset = (filters.page - 1) * filters.page_size
        rows = self.client.query_json(
            f"""
            SELECT result_id, tenant_id, domain, check_type, severity, status,
                   summary_metrics_json, failing_dimensions_json, thresholds_json, rules_version,
                   ingestion_run_id, measured_at, created_by, created_at, updated_at
            FROM data_quality_results_v2
            {where_clause}
            ORDER BY measured_at DESC
            LIMIT {{limit:UInt64}} OFFSET {{offset:UInt64}}
            """,
            {**params, "limit": filters.page_size, "offset": offset},
        )
        items = [_data_quality_from_row(row) for row in rows]
        return items, _build_pagination(filters.page, filters.page_size, total_items)

    def get_data_quality_result(self, *, result_id: str, tenant_id: str) -> DataQualityResultStatus | None:
        rows = self.client.query_json(
            """
            SELECT result_id, tenant_id, domain, check_type, severity, status,
                   summary_metrics_json, failing_dimensions_json, thresholds_json, rules_version,
                   ingestion_run_id, measured_at, created_by, created_at, updated_at
            FROM data_quality_results_v2
            WHERE result_id = {result_id:String} AND tenant_id = {tenant_id:String}
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            {"result_id": result_id, "tenant_id": tenant_id},
        )
        if not rows:
            return None
        return _data_quality_from_row(rows[0])

    def create_data_quality_result(
        self, *, tenant_id: str, created_by: str, payload: DataQualityUpsertRequest
    ) -> DataQualityResultStatus:
        result_id = f"dq_{uuid4().hex}"
        now = datetime.utcnow().isoformat()
        self.client.query_json(
            """
            INSERT INTO data_quality_results_v2
            (result_id, tenant_id, domain, check_type, severity, status, summary_metrics_json,
             failing_dimensions_json, thresholds_json, rules_version, ingestion_run_id, measured_at,
             created_by, created_at, updated_at)
            VALUES
            ({result_id:String}, {tenant_id:String}, {domain:String}, {check_type:String}, {severity:String},
             {status:String}, {summary_metrics_json:String}, {failing_dimensions_json:String},
             {thresholds_json:String}, {rules_version:String}, {ingestion_run_id:String},
             {measured_at:String}::timestamptz, {created_by:String},
             {created_at:String}::timestamptz, {updated_at:String}::timestamptz)
            """,
            {
                "result_id": result_id,
                "tenant_id": tenant_id,
                "domain": payload.domain,
                "check_type": payload.check_type,
                "severity": payload.severity,
                "status": payload.status,
                "summary_metrics_json": json.dumps(payload.summary_metrics, sort_keys=True),
                "failing_dimensions_json": json.dumps(payload.failing_dimensions),
                "thresholds_json": json.dumps(payload.thresholds, sort_keys=True),
                "rules_version": payload.rules_version,
                "ingestion_run_id": payload.ingestion_run_id or "",
                "measured_at": payload.measured_at.isoformat(),
                "created_by": created_by,
                "created_at": now,
                "updated_at": now,
            },
        )
        result = self.get_data_quality_result(result_id=result_id, tenant_id=tenant_id)
        if result is None:
            raise RuntimeError("failed to persist data quality result")
        return result
