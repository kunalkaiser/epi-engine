"""
apps/worker/live_ingestion.py — Live public API ingestion pipeline.

Fetches from three free public sources and writes to ClickHouse staging tables.
Logging goes to ingestion_runs_v2. All tables are created with IF NOT EXISTS DDL.

Sources:
  1. OpenFDA FAERS    — drug/indication terms from adverse event reports
  2. ClinicalTrials.gov — recruiting trial conditions and enrollment counts
  3. OpenTargets       — top 20 diseases by genetic association score

Association is never upgraded to causation. All signals are observational/registry.
"""
from __future__ import annotations

import json
import logging
import os
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib import error, parse, request as _urllib
from uuid import uuid4

from apps.worker.source_adapters import SourceLoadResult


logger = logging.getLogger("epi_engine.worker.live_ingestion")


# ── Auth-aware ClickHouse helper ──────────────────────────────────────────────

def _ch_request(
    base_url: str,
    sql: str,
    payload: bytes = b"",
    *,
    user: str = "",
    password: str = "",
    database: str = "epi_engine",
    timeout: int = 30,
) -> str:
    params: dict[str, str] = {"query": sql, "database": database}
    if user:
        params["user"] = user
    if password:
        params["password"] = password
    endpoint = f"{base_url.rstrip('/')}/?{parse.urlencode(params)}"
    req = _urllib.Request(endpoint, data=payload, method="POST")
    try:
        with _urllib.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except error.URLError as exc:
        raise RuntimeError(f"ClickHouse request failed: {exc}") from exc


# ── Protocol ──────────────────────────────────────────────────────────────────

class LiveSourceAdapter(Protocol):
    source_kind: str

    def fetch(self) -> SourceLoadResult:
        ...


# ── 1. OpenFDA FAERS adapter ──────────────────────────────────────────────────

_OPENFDA_URL = "https://api.fda.gov/drug/event.json?limit=100"
_OPENFDA_SKIP_INDICATIONS = frozenset({
    "", "not specified", "unknown", "n/a", "na", "none", "other",
    "product used for unknown indication",
})


@dataclass(frozen=True)
class OpenFDAAdapter:
    source_kind: str = "openfda_faers_live"

    def fetch(self) -> SourceLoadResult:
        req = _urllib.Request(
            _OPENFDA_URL,
            headers={"Accept": "application/json", "User-Agent": "epi-engine/1.0"},
        )
        with _urllib.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())

        drug_indication: Counter[tuple[str, str]] = Counter()
        for event in data.get("results", []):
            for drug in event.get("patient", {}).get("drug", []):
                generic_names = drug.get("openfda", {}).get("generic_name") or []
                indication = (drug.get("drugindication") or "").strip().lower()
                if indication in _OPENFDA_SKIP_INDICATIONS:
                    continue
                for raw_name in generic_names[:1]:
                    name = raw_name.strip().lower()
                    if name:
                        drug_indication[(name, indication)] += 1

        fetched_at = datetime.now(UTC).isoformat()
        rows = [
            {
                "drug_name": drug,
                "indication_term": indication,
                "report_count": count,
                "source_url": _OPENFDA_URL,
                "fetched_at": fetched_at,
            }
            for (drug, indication), count in drug_indication.most_common(200)
        ]
        return SourceLoadResult(
            rows=rows,
            source_system="openfda_faers",
            provenance={
                "url": _OPENFDA_URL,
                "raw_events": len(data.get("results", [])),
                "unique_drug_indication_pairs": len(drug_indication),
            },
            freshness_timestamp=fetched_at,
        )


# ── 2. ClinicalTrials.gov adapter ─────────────────────────────────────────────

_CT_URL = (
    "https://clinicaltrials.gov/api/v2/studies"
    "?format=json&pageSize=100&filter.overallStatus=RECRUITING"
)


@dataclass(frozen=True)
class ClinicalTrialsAdapter:
    source_kind: str = "clinicaltrials_gov_live"

    def fetch(self) -> SourceLoadResult:
        req = _urllib.Request(
            _CT_URL,
            headers={"Accept": "application/json", "User-Agent": "epi-engine/1.0"},
        )
        with _urllib.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())

        fetched_at = datetime.now(UTC).isoformat()
        rows: list[dict[str, Any]] = []
        for study in data.get("studies", []):
            proto = study.get("protocolSection", {})
            nct_id = proto.get("identificationModule", {}).get("nctId", "")
            status = proto.get("statusModule", {}).get("overallStatus", "")
            phases = proto.get("designModule", {}).get("phases") or []
            phase = ", ".join(phases) if phases else "N/A"
            enrollment = int(
                (proto.get("designModule", {}).get("enrollmentInfo") or {}).get("count") or 0
            )
            conditions = proto.get("conditionsModule", {}).get("conditions") or []
            for condition in conditions[:3]:
                c = condition.strip().lower()
                if c:
                    rows.append({
                        "nct_id": nct_id,
                        "condition": c,
                        "phase": phase,
                        "enrollment": enrollment,
                        "status": status,
                        "source_url": _CT_URL,
                        "fetched_at": fetched_at,
                    })

        return SourceLoadResult(
            rows=rows,
            source_system="clinicaltrials_gov",
            provenance={
                "url": _CT_URL,
                "total_studies": data.get("totalCount", 0),
                "studies_fetched": len(data.get("studies", [])),
            },
            freshness_timestamp=fetched_at,
        )


# ── 3. OpenTargets adapter ────────────────────────────────────────────────────

_OT_URL = "https://api.platform.opentargets.org/api/v4/graphql"
_OT_QUERY = """{
  search(queryString: "disease", entityNames: ["disease"], page: {index: 0, size: 20}) {
    hits { id name score }
  }
}"""


@dataclass(frozen=True)
class OpenTargetsAdapter:
    source_kind: str = "open_targets_live"

    def fetch(self) -> SourceLoadResult:
        payload = json.dumps({"query": _OT_QUERY}).encode()
        req = _urllib.Request(
            _OT_URL,
            data=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        with _urllib.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())

        hits = (data.get("data") or {}).get("search", {}).get("hits") or []
        fetched_at = datetime.now(UTC).isoformat()
        rows = [
            {
                "disease_id": hit.get("id", ""),
                "disease_name": hit.get("name", ""),
                "genetic_association_score": round(float(hit.get("score") or 0.0), 4),
                "source_url": _OT_URL,
                "fetched_at": fetched_at,
            }
            for hit in hits
            if hit.get("id")
        ]
        return SourceLoadResult(
            rows=rows,
            source_system="open_targets",
            provenance={"url": _OT_URL, "hits_returned": len(hits)},
            freshness_timestamp=fetched_at,
        )


# ── Adapter registry ──────────────────────────────────────────────────────────

LIVE_ADAPTERS: list[LiveSourceAdapter] = [
    OpenFDAAdapter(),
    ClinicalTrialsAdapter(),
    OpenTargetsAdapter(),
]


# ── ClickHouse table DDL (IF NOT EXISTS) ──────────────────────────────────────

_DDL_FAERS = """
CREATE TABLE IF NOT EXISTS epi_engine.live_faers_signals (
    drug_name       String,
    indication_term String,
    report_count    UInt32,
    source_url      String,
    fetched_at      DateTime64(3, 'UTC')
) ENGINE = ReplacingMergeTree(fetched_at)
ORDER BY (drug_name, indication_term)
"""

_DDL_CT = """
CREATE TABLE IF NOT EXISTS epi_engine.live_clinical_trials (
    nct_id      String,
    condition   String,
    phase       String,
    enrollment  UInt32,
    status      String,
    source_url  String,
    fetched_at  DateTime64(3, 'UTC')
) ENGINE = ReplacingMergeTree(fetched_at)
ORDER BY (nct_id, condition)
"""

_DDL_OT = """
CREATE TABLE IF NOT EXISTS epi_engine.live_open_targets_diseases (
    disease_id                String,
    disease_name              String,
    genetic_association_score Float64,
    source_url                String,
    fetched_at                DateTime64(3, 'UTC')
) ENGINE = ReplacingMergeTree(fetched_at)
ORDER BY (disease_id)
"""

# Maps source_kind → (target_table_name, create_ddl)
_ADAPTER_CONFIG: dict[str, tuple[str, str]] = {
    "openfda_faers_live":      ("live_faers_signals",             _DDL_FAERS),
    "clinicaltrials_gov_live": ("live_clinical_trials",           _DDL_CT),
    "open_targets_live":       ("live_open_targets_diseases",     _DDL_OT),
}


# ── Ingestion run logger ──────────────────────────────────────────────────────

class _RunStore:
    """Writes a single completed/failed row to ingestion_runs_v2."""

    def __init__(self, base_url: str, user: str, password: str) -> None:
        self._url = base_url
        self._user = user
        self._pw = password

    def record(
        self,
        *,
        run_id: str,
        dataset_name: str,
        source_system: str,
        trigger_source: str,
        status: str,
        records_processed: int,
        records_inserted: int,
        freshness_metric: str,
        provenance_ref: str,
        error_summary: dict[str, Any],
    ) -> None:
        now = datetime.now(UTC).isoformat()
        err_json = json.dumps(json.dumps(error_summary))
        prov = json.dumps(provenance_ref)
        sql = f"""
INSERT INTO epi_engine.ingestion_runs_v2
(run_id, tenant_id, dataset_name, source_system, trigger_source, status, source_ref,
 records_processed, records_inserted, records_updated, records_rejected,
 validation_summary_json, error_summary_json, freshness_metric, provenance_ref, artifact_ref,
 created_by, started_at, completed_at, created_at, updated_at)
VALUES
({json.dumps(run_id)}, 'system', {json.dumps(dataset_name)}, {json.dumps(source_system)},
 {json.dumps(trigger_source)}, {json.dumps(status)}, '',
 {records_processed}, {records_inserted}, 0, 0,
 '{{}}', {err_json}, {json.dumps(freshness_metric)}, {prov}, '',
 'live_ingestion_worker',
 parseDateTimeBestEffort({json.dumps(now)}),
 parseDateTimeBestEffort({json.dumps(now)}),
 parseDateTimeBestEffort({json.dumps(now)}),
 parseDateTimeBestEffort({json.dumps(now)}))
"""
        try:
            _ch_request(self._url, sql, user=self._user, password=self._pw)
        except Exception as exc:
            logger.warning(f"live_ingestion.run_log_failed run_id={run_id} err={exc}")


# ── Per-adapter ingestion ─────────────────────────────────────────────────────

def _ingest_one(
    adapter: LiveSourceAdapter,
    *,
    run_store: _RunStore | None,
    dry_run: bool,
    url: str,
    user: str,
    password: str,
) -> dict[str, Any]:
    source_kind = adapter.source_kind
    table_name, ddl = _ADAPTER_CONFIG[source_kind]
    run_id = f"live_{uuid4().hex}"

    try:
        fetch_result = adapter.fetch()
        rows = fetch_result.rows

        if not dry_run:
            _ch_request(url, ddl, user=user, password=password)
            if rows:
                payload = "\n".join(json.dumps(r) for r in rows).encode()
                insert_sql = f"INSERT INTO epi_engine.{table_name} FORMAT JSONEachRow"
                _ch_request(url, insert_sql, payload, user=user, password=password)
            if run_store:
                run_store.record(
                    run_id=run_id,
                    dataset_name=table_name,
                    source_system=source_kind,
                    trigger_source="scheduled",
                    status="succeeded",
                    records_processed=len(rows),
                    records_inserted=len(rows),
                    freshness_metric=fetch_result.freshness_timestamp,
                    provenance_ref=json.dumps(fetch_result.provenance),
                    error_summary={},
                )

        return {
            "source": source_kind,
            "table": table_name,
            "rows_fetched": len(rows),
            "status": "dry_run" if dry_run else "ok",
            "freshness_timestamp": fetch_result.freshness_timestamp,
            "provenance": fetch_result.provenance,
        }

    except Exception as exc:
        logger.error(f"live_ingestion.adapter_failed source={source_kind} error={exc}")
        if not dry_run and run_store:
            try:
                run_store.record(
                    run_id=run_id,
                    dataset_name=table_name,
                    source_system=source_kind,
                    trigger_source="scheduled",
                    status="failed",
                    records_processed=0,
                    records_inserted=0,
                    freshness_metric="",
                    provenance_ref="",
                    error_summary={"error": str(exc)},
                )
            except Exception:
                pass
        return {
            "source": source_kind,
            "table": table_name,
            "rows_fetched": 0,
            "status": "error",
            "error": str(exc),
        }


# ── Public entry point ────────────────────────────────────────────────────────

def run_live_ingestion(
    *,
    dry_run: bool = False,
    clickhouse_url: str | None = None,
    clickhouse_user: str | None = None,
    clickhouse_password: str | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch from all live adapters and write to ClickHouse.

    dry_run=True: fetches from APIs and prints row counts but writes nothing.

    Returns one result dict per adapter with keys:
      source, table, rows_fetched, status, freshness_timestamp, provenance
    """
    url = (clickhouse_url or os.getenv("CLICKHOUSE_URL", "http://localhost:8123")).rstrip("/")
    user = clickhouse_user or os.getenv("CLICKHOUSE_USER", "default")
    password = clickhouse_password or os.getenv("CLICKHOUSE_PASSWORD", "")

    run_store = _RunStore(url, user, password) if not dry_run else None

    results: list[dict[str, Any]] = []
    for adapter in LIVE_ADAPTERS:
        result = _ingest_one(
            adapter,
            run_store=run_store,
            dry_run=dry_run,
            url=url,
            user=user,
            password=password,
        )
        results.append(result)

    return results
