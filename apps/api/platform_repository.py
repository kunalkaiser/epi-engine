from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from math import ceil
from typing import Any
from uuid import uuid4

from apps.api.db import ClickHouseClient, ClickHouseConfig
from apps.api.platform_models import (
    DataQualityUpsertRequest,
    DataQualityResultStatus,
    IngestionRunStatusSummary,
    MethodologyMetadata,
    SimulationResultItem,
    SimulationRunCompareRequest,
    SimulationComparisonResponse,
    SimulationDeltaItem,
    SimulationRunSummary,
)
from apps.api.query_models import DataQualityRunsFilters, IngestionRunsFilters, SimulationRunsFilters
from apps.api.response_models import PaginationMeta
from apps.api.settings import get_settings


@dataclass(frozen=True)
class SimulationRunRecord:
    summary: SimulationRunSummary
    assumptions: dict[str, Any]
    items: list[SimulationResultItem]


class PlatformPersistenceRepository:
    def __init__(self, client: ClickHouseClient) -> None:
        self.client = client

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
            (
                run_id,
                tenant_id,
                status,
                scenario_type,
                region_code,
                created_by,
                trigger_source,
                assumptions_json,
                methodology_json,
                attempt_count,
                max_attempts,
                created_at,
                updated_at
            )
            VALUES
            (
                {run_id:String},
                {tenant_id:String},
                'queued',
                {scenario_type:String},
                {region_code:String},
                {created_by:String},
                {trigger_source:String},
                {assumptions_json:String},
                {methodology_json:String},
                0,
                {max_attempts:UInt8},
                parseDateTimeBestEffort({created_at:String}),
                parseDateTimeBestEffort({updated_at:String})
            )
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
            INSERT INTO simulation_runs
            (
                run_id,
                tenant_id,
                status,
                scenario_type,
                region_code,
                created_by,
                trigger_source,
                assumptions_json,
                methodology_json,
                result_summary,
                artifact_ref,
                error_message,
                attempt_count,
                max_attempts,
                created_at,
                updated_at
            )
            VALUES
            (
                {run_id:String},
                {tenant_id:String},
                {status:String},
                {scenario_type:String},
                {region_code:String},
                {created_by:String},
                {trigger_source:String},
                {assumptions_json:String},
                {methodology_json:String},
                {result_summary:String},
                {artifact_ref:String},
                {error_message:String},
                {attempt_count:UInt8},
                {max_attempts:UInt8},
                parseDateTimeBestEffort({created_at:String}),
                parseDateTimeBestEffort({updated_at:String})
            )
            """,
            {
                "run_id": run_id,
                "tenant_id": tenant_id,
                "status": status,
                "scenario_type": current.summary.scenario_type,
                "region_code": current.summary.region or "",
                "created_by": current.summary.created_by,
                "trigger_source": current.summary.trigger_source,
                "assumptions_json": json.dumps(current.assumptions, sort_keys=True),
                "methodology_json": current.summary.methodology.model_dump_json(),
                "result_summary": result_summary or current.summary.result_summary or "",
                "artifact_ref": artifact_ref or current.summary.artifact_ref or "",
                "error_message": error_message or current.summary.error_message or "",
                "attempt_count": attempt_count if attempt_count is not None else current.summary.attempt_count,
                "max_attempts": current.summary.max_attempts,
                "created_at": current.summary.created_at.isoformat(),
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
        for item in items:
            self.client.query_json(
                """
                INSERT INTO simulation_run_items
                (
                    run_id,
                    tenant_id,
                    indication_id,
                    indication_name,
                    baseline_score,
                    simulated_score,
                    score_delta,
                    uncertainty_low,
                    uncertainty_high,
                    outcome_drivers_json,
                    score_inputs_json,
                    trace_id,
                    created_at
                )
                VALUES
                (
                    {run_id:String},
                    {tenant_id:String},
                    {indication_id:String},
                    {indication_name:String},
                    {baseline_score:Float64},
                    {simulated_score:Float64},
                    {score_delta:Float64},
                    {uncertainty_low:Float64},
                    {uncertainty_high:Float64},
                    {outcome_drivers_json:String},
                    {score_inputs_json:String},
                    {trace_id:String},
                    now()
                )
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
            SELECT
                run_id,
                tenant_id,
                status,
                scenario_type,
                region_code,
                created_by,
                trigger_source,
                assumptions_json,
                methodology_json,
                result_summary,
                artifact_ref,
                error_message,
                attempt_count,
                max_attempts,
                created_at,
                updated_at
            FROM simulation_runs
            WHERE run_id = {run_id:String} AND tenant_id = {tenant_id:String}
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            {"run_id": run_id, "tenant_id": tenant_id},
        )
        if not rows:
            return None
        row = rows[0]
        item_rows = self.client.query_json(
            """
            SELECT
                indication_id,
                indication_name,
                baseline_score,
                simulated_score,
                score_delta
                ,
                uncertainty_low,
                uncertainty_high,
                outcome_drivers_json,
                score_inputs_json,
                trace_id
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

    def list_simulation_runs(self, *, tenant_id: str, filters: SimulationRunsFilters) -> tuple[list[SimulationRunSummary], PaginationMeta]:
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
            f"SELECT countDistinct(run_id) AS total_items FROM simulation_runs {where_clause}",
            params,
        )
        total_items = int(count_rows[0]["total_items"]) if count_rows else 0
        offset = (filters.page - 1) * filters.page_size
        rows = self.client.query_json(
            f"""
            SELECT
                run_id,
                tenant_id,
                anyLast(status) AS status,
                anyLast(scenario_type) AS scenario_type,
                anyLast(region_code) AS region_code,
                anyLast(created_by) AS created_by,
                anyLast(trigger_source) AS trigger_source,
                anyLast(methodology_json) AS methodology_json,
                anyLast(result_summary) AS result_summary,
                anyLast(artifact_ref) AS artifact_ref,
                anyLast(error_message) AS error_message,
                anyLast(attempt_count) AS attempt_count,
                anyLast(max_attempts) AS max_attempts,
                min(created_at) AS created_at,
                max(updated_at) AS updated_at
            FROM simulation_runs
            {where_clause}
            GROUP BY run_id, tenant_id
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
            SELECT
                run_id,
                tenant_id
            FROM
            (
                SELECT
                    run_id,
                    tenant_id,
                    argMax(status, updated_at) AS status,
                    anyLast(created_at) AS created_at
                FROM simulation_runs
                GROUP BY run_id, tenant_id
            )
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
            (
                event_id,
                run_id,
                tenant_id,
                event_type,
                detail_json,
                created_at
            )
            VALUES
            (
                {event_id:String},
                {run_id:String},
                {tenant_id:String},
                {event_type:String},
                {detail_json:String},
                now()
            )
            """,
            {
                "event_id": f"sev_{uuid4().hex}",
                "run_id": run_id,
                "tenant_id": tenant_id,
                "event_type": event_type,
                "detail_json": json.dumps(detail, sort_keys=True),
            },
        )

    def cancel_simulation_run(self, *, run_id: str, tenant_id: str) -> bool:
        current = self.get_simulation_run(run_id=run_id, tenant_id=tenant_id)
        if current is None:
            return False
        if current.summary.status in {"succeeded", "failed", "cancelled"}:
            return False
        self.update_simulation_run(run_id=run_id, tenant_id=tenant_id, status="cancelled")
        return True

    def compare_simulation_runs(
        self, *, tenant_id: str, request: SimulationRunCompareRequest
    ) -> SimulationComparisonResponse:
        records: list[SimulationRunRecord] = []
        for run_id in request.run_ids:
            record = self.get_simulation_run(run_id=run_id, tenant_id=tenant_id)
            if record is None:
                raise LookupError(f"simulation run not found: {run_id}")
            records.append(record)

        assumption_deltas: dict[str, list[str]] = {}
        all_assumption_keys = sorted({key for record in records for key in record.assumptions.keys()})
        for key in all_assumption_keys:
            values = [json.dumps(record.assumptions.get(key, None), sort_keys=True) for record in records]
            if len(set(values)) > 1:
                assumption_deltas[key] = values

        by_indication: dict[str, dict[str, Any]] = {}
        for record in records:
            for item in record.items:
                agg = by_indication.setdefault(
                    item.indication_id,
                    {"name": item.indication_name, "scores": {}},
                )
                agg["scores"][record.summary.run_id] = item.simulated_score

        deltas: list[SimulationDeltaItem] = []
        for indication_id, payload in by_indication.items():
            scores = payload["scores"]
            if len(scores) < 2:
                continue
            min_score = min(scores.values())
            max_score = max(scores.values())
            deltas.append(
                SimulationDeltaItem(
                    indication_id=indication_id,
                    indication_name=payload["name"],
                    min_score=min_score,
                    max_score=max_score,
                    score_spread=round(max_score - min_score, 4),
                    run_scores=scores,
                )
            )
        deltas.sort(key=lambda item: item.score_spread, reverse=True)
        return SimulationComparisonResponse(
            tenant_id=tenant_id,
            compared_run_ids=request.run_ids,
            assumption_deltas=assumption_deltas,
            score_deltas=deltas,
            generated_at=datetime.utcnow(),
        )

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
            where_parts.append("started_at >= parseDateTimeBestEffort({date_from:String})")
            params["date_from"] = f"{filters.date_from.isoformat()}T00:00:00"
        if filters.date_to:
            where_parts.append("started_at <= parseDateTimeBestEffort({date_to:String})")
            params["date_to"] = f"{filters.date_to.isoformat()}T23:59:59"
        where_clause = f"WHERE {' AND '.join(where_parts)}"
        count_rows = self.client.query_json(
            f"SELECT countDistinct(run_id) AS total_items FROM ingestion_runs_v2 {where_clause}",
            params,
        )
        total_items = int(count_rows[0]["total_items"]) if count_rows else 0
        offset = (filters.page - 1) * filters.page_size
        rows = self.client.query_json(
            f"""
            SELECT
                run_id,
                tenant_id,
                anyLast(dataset_name) AS dataset_name,
                anyLast(source_system) AS source_system,
                anyLast(trigger_source) AS trigger_source,
                anyLast(status) AS status,
                anyLast(records_processed) AS records_processed,
                anyLast(records_inserted) AS records_inserted,
                anyLast(records_updated) AS records_updated,
                anyLast(records_rejected) AS records_rejected,
                anyLast(validation_summary_json) AS validation_summary_json,
                anyLast(error_summary_json) AS error_summary_json,
                anyLast(freshness_metric) AS freshness_metric,
                anyLast(provenance_ref) AS provenance_ref,
                anyLast(artifact_ref) AS artifact_ref,
                anyLast(created_by) AS created_by,
                min(started_at) AS started_at,
                max(completed_at) AS completed_at,
                min(created_at) AS created_at,
                max(updated_at) AS updated_at
            FROM ingestion_runs_v2
            {where_clause}
            GROUP BY run_id, tenant_id
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
            SELECT
                run_id,
                tenant_id,
                dataset_name,
                source_system,
                trigger_source,
                status,
                records_processed,
                records_inserted,
                records_updated,
                records_rejected,
                validation_summary_json,
                error_summary_json,
                freshness_metric,
                provenance_ref,
                artifact_ref,
                created_by,
                started_at,
                completed_at,
                created_at,
                updated_at
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
            where_parts.append("measured_at >= parseDateTimeBestEffort({date_from:String})")
            params["date_from"] = f"{filters.date_from.isoformat()}T00:00:00"
        if filters.date_to:
            where_parts.append("measured_at <= parseDateTimeBestEffort({date_to:String})")
            params["date_to"] = f"{filters.date_to.isoformat()}T23:59:59"
        where_clause = f"WHERE {' AND '.join(where_parts)}"
        count_rows = self.client.query_json(
            f"SELECT countDistinct(result_id) AS total_items FROM data_quality_results_v2 {where_clause}",
            params,
        )
        total_items = int(count_rows[0]["total_items"]) if count_rows else 0
        offset = (filters.page - 1) * filters.page_size
        rows = self.client.query_json(
            f"""
            SELECT
                result_id,
                tenant_id,
                domain,
                check_type,
                severity,
                status,
                summary_metrics_json,
                failing_dimensions_json,
                thresholds_json,
                rules_version,
                ingestion_run_id,
                measured_at,
                created_by,
                created_at,
                updated_at
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
            SELECT
                result_id,
                tenant_id,
                domain,
                check_type,
                severity,
                status,
                summary_metrics_json,
                failing_dimensions_json,
                thresholds_json,
                rules_version,
                ingestion_run_id,
                measured_at,
                created_by,
                created_at,
                updated_at
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
            (
                result_id,
                tenant_id,
                domain,
                check_type,
                severity,
                status,
                summary_metrics_json,
                failing_dimensions_json,
                thresholds_json,
                rules_version,
                ingestion_run_id,
                measured_at,
                created_by,
                created_at,
                updated_at
            )
            VALUES
            (
                {result_id:String},
                {tenant_id:String},
                {domain:String},
                {check_type:String},
                {severity:String},
                {status:String},
                {summary_metrics_json:String},
                {failing_dimensions_json:String},
                {thresholds_json:String},
                {rules_version:String},
                {ingestion_run_id:String},
                parseDateTimeBestEffort({measured_at:String}),
                {created_by:String},
                parseDateTimeBestEffort({created_at:String}),
                parseDateTimeBestEffort({updated_at:String})
            )
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


def build_platform_repository() -> PlatformPersistenceRepository:
    settings = get_settings()
    client = ClickHouseClient(
        ClickHouseConfig(
            base_url=settings.clickhouse_url,
            database=settings.clickhouse_database,
            user=settings.clickhouse_user,
            password=settings.clickhouse_password,
            timeout_seconds=settings.clickhouse_timeout_seconds,
        )
    )
    # Probe for deterministic startup failure if unavailable.
    client.query_json("SELECT 1 AS ok")
    return PlatformPersistenceRepository(client)


def _build_pagination(page: int, page_size: int, total_items: int) -> PaginationMeta:
    total_pages = ceil(total_items / page_size) if total_items else 0
    return PaginationMeta(page=page, page_size=page_size, total_items=total_items, total_pages=total_pages)


def _simulation_summary_from_row(row: dict[str, Any]) -> SimulationRunSummary:
    methodology = MethodologyMetadata.model_validate(json.loads(row["methodology_json"]))
    return SimulationRunSummary(
        run_id=row["run_id"],
        tenant_id=row["tenant_id"],
        status=row["status"],
        scenario_type=row["scenario_type"],
        region=row.get("region_code") or None,
        created_by=row["created_by"],
        trigger_source=row["trigger_source"],
        result_summary=row.get("result_summary") or None,
        artifact_ref=row.get("artifact_ref") or None,
        error_message=row.get("error_message") or None,
        methodology=methodology,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        attempt_count=int(row.get("attempt_count", 0)),
        max_attempts=int(row.get("max_attempts", 2)),
    )


def _ingestion_summary_from_row(row: dict[str, Any]) -> IngestionRunStatusSummary:
    return IngestionRunStatusSummary(
        run_id=row["run_id"],
        tenant_id=row["tenant_id"],
        dataset_name=row["dataset_name"],
        source_system=row["source_system"],
        trigger_source=row["trigger_source"],
        status=row["status"],
        records_processed=int(row["records_processed"]),
        records_inserted=int(row["records_inserted"]),
        records_updated=int(row["records_updated"]),
        records_rejected=int(row["records_rejected"]),
        validation_summary=json.loads(row.get("validation_summary_json") or "{}"),
        error_summary=json.loads(row.get("error_summary_json") or "{}"),
        freshness_metric=row.get("freshness_metric") or None,
        provenance_ref=row.get("provenance_ref") or None,
        artifact_ref=row.get("artifact_ref") or None,
        created_by=row["created_by"],
        started_at=row["started_at"],
        completed_at=row.get("completed_at"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _data_quality_from_row(row: dict[str, Any]) -> DataQualityResultStatus:
    return DataQualityResultStatus(
        result_id=row["result_id"],
        tenant_id=row["tenant_id"],
        domain=row["domain"],
        check_type=row["check_type"],
        severity=row["severity"],
        status=row["status"],
        summary_metrics=json.loads(row.get("summary_metrics_json") or "{}"),
        failing_dimensions=json.loads(row.get("failing_dimensions_json") or "[]"),
        thresholds=json.loads(row.get("thresholds_json") or "{}"),
        rules_version=row["rules_version"],
        ingestion_run_id=row.get("ingestion_run_id") or None,
        measured_at=row["measured_at"],
        created_by=row["created_by"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
