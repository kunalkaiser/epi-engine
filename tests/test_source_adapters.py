from pathlib import Path

from apps.worker.source_adapters import get_source_adapter, supported_source_kinds


def test_supported_source_kinds_includes_enterprise_boundaries() -> None:
    supported = supported_source_kinds()
    assert "synthetic" in supported
    assert "ehr_aggregate" in supported
    assert "claims_aggregate" in supported
    assert "registry_aggregate" in supported
    assert "genomic_summary" in supported
    assert "benchmark_reference" in supported
    assert "literature_metadata" in supported


def test_source_adapter_emits_provenance_and_freshness(tmp_path: Path) -> None:
    sample = tmp_path / "sample.csv"
    sample.write_text(
        "population_label,age_band,sex,count\nAdults with T2D,45-64,female,18240\n",
        encoding="utf-8",
    )
    adapter = get_source_adapter("ehr_aggregate")
    result = adapter.load(sample)

    assert len(result.rows) == 1
    assert result.source_system == "ehr_aggregate_feed"
    assert result.provenance["adapter"] == "ehr_aggregate"
    assert result.provenance["integration_boundary"] == "enterprise_connector_required_for_live_feed"
    assert result.freshness_timestamp
