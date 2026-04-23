from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import pandas as pd


@dataclass(frozen=True)
class SourceLoadResult:
    rows: list[dict[str, Any]]
    source_system: str
    provenance: dict[str, Any]
    freshness_timestamp: str


class SourceAdapter(Protocol):
    source_kind: str

    def load(self, input_path: Path) -> SourceLoadResult:
        ...


def get_source_adapter(source_kind: str) -> SourceAdapter:
    adapter = ADAPTER_REGISTRY.get(source_kind)
    if adapter is None:
        raise ValueError(f"unsupported source_kind: {source_kind}")
    return adapter


def supported_source_kinds() -> list[str]:
    return sorted(ADAPTER_REGISTRY.keys())


def _load_rows(input_path: Path) -> list[dict[str, Any]]:
    suffix = input_path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(input_path).to_dict(orient="records")
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(input_path).to_dict(orient="records")
    raise ValueError(f"unsupported file extension: {suffix}")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class LocalSyntheticAdapter:
    source_kind: str = "synthetic"

    def load(self, input_path: Path) -> SourceLoadResult:
        rows = _load_rows(input_path)
        return SourceLoadResult(
            rows=rows,
            source_system="local_synthetic_fixture",
            provenance={
                "adapter": self.source_kind,
                "path": str(input_path),
                "mode": "development_fixture",
            },
            freshness_timestamp=_now_iso(),
        )


@dataclass(frozen=True)
class EHRAggregateAdapter:
    source_kind: str = "ehr_aggregate"

    def load(self, input_path: Path) -> SourceLoadResult:
        rows = _load_rows(input_path)
        return SourceLoadResult(
            rows=rows,
            source_system="ehr_aggregate_feed",
            provenance={
                "adapter": self.source_kind,
                "path": str(input_path),
                "integration_boundary": "enterprise_connector_required_for_live_feed",
            },
            freshness_timestamp=_now_iso(),
        )


@dataclass(frozen=True)
class ClaimsAggregateAdapter:
    source_kind: str = "claims_aggregate"

    def load(self, input_path: Path) -> SourceLoadResult:
        rows = _load_rows(input_path)
        return SourceLoadResult(
            rows=rows,
            source_system="claims_aggregate_feed",
            provenance={
                "adapter": self.source_kind,
                "path": str(input_path),
                "integration_boundary": "enterprise_connector_required_for_live_feed",
            },
            freshness_timestamp=_now_iso(),
        )


@dataclass(frozen=True)
class RegistryAggregateAdapter:
    source_kind: str = "registry_aggregate"

    def load(self, input_path: Path) -> SourceLoadResult:
        rows = _load_rows(input_path)
        return SourceLoadResult(
            rows=rows,
            source_system="registry_cohort_summary_feed",
            provenance={
                "adapter": self.source_kind,
                "path": str(input_path),
                "integration_boundary": "enterprise_connector_required_for_live_feed",
            },
            freshness_timestamp=_now_iso(),
        )


@dataclass(frozen=True)
class GenomicSummaryAdapter:
    source_kind: str = "genomic_summary"

    def load(self, input_path: Path) -> SourceLoadResult:
        rows = _load_rows(input_path)
        return SourceLoadResult(
            rows=rows,
            source_system="genomic_biomarker_summary_feed",
            provenance={
                "adapter": self.source_kind,
                "path": str(input_path),
                "integration_boundary": "enterprise_connector_required_for_live_feed",
            },
            freshness_timestamp=_now_iso(),
        )


@dataclass(frozen=True)
class BenchmarkReferenceAdapter:
    source_kind: str = "benchmark_reference"

    def load(self, input_path: Path) -> SourceLoadResult:
        rows = _load_rows(input_path)
        return SourceLoadResult(
            rows=rows,
            source_system="external_benchmark_reference",
            provenance={
                "adapter": self.source_kind,
                "path": str(input_path),
                "integration_boundary": "enterprise_connector_required_for_live_feed",
            },
            freshness_timestamp=_now_iso(),
        )


@dataclass(frozen=True)
class LiteratureMetadataAdapter:
    source_kind: str = "literature_metadata"

    def load(self, input_path: Path) -> SourceLoadResult:
        rows = _load_rows(input_path)
        return SourceLoadResult(
            rows=rows,
            source_system="literature_metadata_feed",
            provenance={
                "adapter": self.source_kind,
                "path": str(input_path),
                "integration_boundary": "enterprise_connector_required_for_live_feed",
            },
            freshness_timestamp=_now_iso(),
        )


ADAPTER_REGISTRY: dict[str, SourceAdapter] = {
    "synthetic": LocalSyntheticAdapter(),
    "ehr_aggregate": EHRAggregateAdapter(),
    "claims_aggregate": ClaimsAggregateAdapter(),
    "registry_aggregate": RegistryAggregateAdapter(),
    "genomic_summary": GenomicSummaryAdapter(),
    "benchmark_reference": BenchmarkReferenceAdapter(),
    "literature_metadata": LiteratureMetadataAdapter(),
}
