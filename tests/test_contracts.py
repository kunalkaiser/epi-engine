from pydantic import ValidationError
import pytest

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


def test_examples_validate() -> None:
    assert PatientSummary.model_validate(PatientSummary.model_config["json_schema_extra"]["example"]).count == 18240
    assert Diagnosis.model_validate(Diagnosis.model_config["json_schema_extra"]["example"]).code == "E11.9"
    assert Medication.model_validate(Medication.model_config["json_schema_extra"]["example"]).name == "Metformin"
    assert LabResult.model_validate(LabResult.model_config["json_schema_extra"]["example"]).interpretation == "high"
    assert Encounter.model_validate(Encounter.model_config["json_schema_extra"]["example"]).region_code == "US-CA"
    assert IncidenceAggregate.model_validate(
        IncidenceAggregate.model_config["json_schema_extra"]["example"]
    ).incident_cases == 1540000
    assert PrevalenceAggregate.model_validate(
        PrevalenceAggregate.model_config["json_schema_extra"]["example"]
    ).prevalent_cases == 32200000
    assert IndicationScore.model_validate(
        IndicationScore.model_config["json_schema_extra"]["example"]
    ).total_score == 68.8


def test_patient_summary_rejects_invalid_age_band() -> None:
    with pytest.raises(ValidationError):
        PatientSummary(
            population_label="Adults with type 2 diabetes",
            age_band="adult",
            sex="female",
            count=25,
        )


def test_lab_result_rejects_invalid_reference_range() -> None:
    with pytest.raises(ValidationError):
        LabResult(
            test_code="A1C",
            test_name="Hemoglobin A1c",
            value=7.2,
            unit="%",
            reference_low=6.0,
            reference_high=5.0,
            interpretation="high",
            collected_on="2026-03-01",
        )


def test_encounter_rejects_reversed_period() -> None:
    with pytest.raises(ValidationError):
        Encounter(
            encounter_type="outpatient",
            region_code="US-CA",
            period_start="2025-12-31",
            period_end="2025-01-01",
            aggregate_count=10,
        )


def test_indication_score_rejects_mismatched_total() -> None:
    with pytest.raises(ValidationError):
        IndicationScore(
            indication_id="t2d-us",
            indication_name="Type 2 diabetes",
            incidence_score=84,
            unmet_need_score=61,
            market_size_score=88,
            competition_score=42,
            total_score=75,
        )
