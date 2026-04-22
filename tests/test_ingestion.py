import json

import pandas as pd
import pytest

from apps.worker.ingestion import InMemoryStagingStore, ingest_file


def test_ingest_csv_separates_valid_and_invalid_rows(tmp_path) -> None:
    input_path = tmp_path / "synthetic_patient_summary.csv"
    input_path.write_text(
        "\n".join(
            [
                "population_label,age_band,sex,count",
                "Adults with type 2 diabetes,45-64,female,18240",
                "Adults with type 2 diabetes,adult,female,9",
            ]
        ),
        encoding="utf-8",
    )
    report_path = tmp_path / "ingestion-report.json"
    staging_store = InMemoryStagingStore()

    result = ingest_file(
        dataset="patient_summary",
        input_path=input_path,
        source_kind="synthetic",
        staging_store=staging_store,
        report_path=report_path,
    )

    assert result.summary.total_rows == 2
    assert result.summary.valid_rows == 1
    assert result.summary.invalid_rows == 1
    assert staging_store.tables["staging_patient_summary"] == [
        {
            "population_label": "Adults with type 2 diabetes",
            "age_band": "45-64",
            "sex": "female",
            "count": 18240,
        }
    ]
    assert result.invalid_rows[0].row_number == 2
    assert "age_band:" in result.invalid_rows[0].errors[0]

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["summary"]["staging_table"] == "staging_patient_summary"
    assert report["summary"]["invalid_rows"] == 1
    assert report["invalid_rows"][0]["row_number"] == 2


def test_ingest_parquet_uses_registered_schema(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_path = tmp_path / "synthetic_diagnosis.parquet"
    input_path.write_bytes(b"placeholder")
    staging_store = InMemoryStagingStore()

    def fake_read_parquet(path):
        assert path == input_path
        return pd.DataFrame(
            [
                {
                    "code": "E11.9",
                    "system": "ICD10",
                    "label": "Type 2 diabetes mellitus without complications",
                    "prevalence_per_100k": 9630.5,
                },
                {
                    "code": "bad code",
                    "system": "ICD10",
                    "label": "Invalid diagnosis",
                    "prevalence_per_100k": 10.0,
                },
            ]
        )

    monkeypatch.setattr(pd, "read_parquet", fake_read_parquet)

    result = ingest_file(
        dataset="diagnosis",
        input_path=input_path,
        source_kind="synthetic",
        staging_store=staging_store,
    )

    assert result.summary.valid_rows == 1
    assert result.summary.invalid_rows == 1
    assert staging_store.tables["staging_diagnosis"][0]["code"] == "E11.9"
    assert result.invalid_rows[0].row_number == 2


def test_ingest_rejects_non_synthetic_sources(tmp_path) -> None:
    input_path = tmp_path / "patient_summary.csv"
    input_path.write_text(
        "\n".join(
            [
                "population_label,age_band,sex,count",
                "Adults with type 2 diabetes,45-64,female,18240",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="synthetic data sources"):
        ingest_file(
            dataset="patient_summary",
            input_path=input_path,
            source_kind="production",
            staging_store=InMemoryStagingStore(),
        )


def test_ingest_rejects_missing_input_file(tmp_path) -> None:
    missing_path = tmp_path / "missing.csv"

    try:
        ingest_file(
            dataset="patient_summary",
            input_path=missing_path,
            source_kind="synthetic",
            staging_store=InMemoryStagingStore(),
        )
    except FileNotFoundError as exc:
        assert str(missing_path) in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError")
