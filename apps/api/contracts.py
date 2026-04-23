from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Sex = Literal["female", "male", "unknown"]
DiagnosisSystem = Literal["ICD10", "SNOMED"]
MedicationRoute = Literal["oral", "injectable", "infusion", "topical", "other"]
MedicationStatus = Literal["marketed", "pipeline", "generic", "discontinued"]
LabInterpretation = Literal["low", "normal", "high", "critical", "unknown"]
EncounterType = Literal["inpatient", "outpatient", "ed", "telehealth", "other"]


class ContractModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class PatientSummary(ContractModel):
    population_label: str = Field(min_length=1, max_length=120)
    age_band: str = Field(pattern=r"^(\d{1,3}-\d{1,3}|\d{1,3}\+|unknown)$")
    sex: Sex
    count: int = Field(ge=0)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "population_label": "Adults with type 2 diabetes",
                "age_band": "45-64",
                "sex": "female",
                "count": 18240,
            }
        },
    )


class Diagnosis(ContractModel):
    code: str = Field(min_length=3, max_length=20, pattern=r"^[A-Z0-9.-]+$")
    system: DiagnosisSystem
    label: str = Field(min_length=1, max_length=160)
    prevalence_per_100k: float | None = Field(default=None, ge=0)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "code": "E11.9",
                "system": "ICD10",
                "label": "Type 2 diabetes mellitus without complications",
                "prevalence_per_100k": 9630.5,
            }
        },
    )


class Medication(ContractModel):
    name: str = Field(min_length=1, max_length=120)
    route: MedicationRoute
    status: MedicationStatus
    competition_class: str = Field(min_length=1, max_length=120)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "name": "Metformin",
                "route": "oral",
                "status": "generic",
                "competition_class": "biguanide",
            }
        },
    )


class LabResult(ContractModel):
    test_code: str = Field(min_length=1, max_length=40, pattern=r"^[A-Z0-9.-]+$")
    test_name: str = Field(min_length=1, max_length=120)
    value: float
    unit: str = Field(min_length=1, max_length=32)
    reference_low: float | None = None
    reference_high: float | None = None
    interpretation: LabInterpretation
    collected_on: date

    @model_validator(mode="after")
    def validate_reference_range(self) -> "LabResult":
        if (
            self.reference_low is not None
            and self.reference_high is not None
            and self.reference_high < self.reference_low
        ):
            raise ValueError("reference_high must be greater than or equal to reference_low")
        return self

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "test_code": "A1C",
                "test_name": "Hemoglobin A1c",
                "value": 7.2,
                "unit": "%",
                "reference_low": 4.0,
                "reference_high": 5.6,
                "interpretation": "high",
                "collected_on": "2026-03-01",
            }
        },
    )


class Encounter(ContractModel):
    encounter_type: EncounterType
    region_code: str = Field(min_length=2, max_length=16, pattern=r"^[A-Z]{2}(-[A-Z0-9]{1,8})?$")
    period_start: date
    period_end: date
    aggregate_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_period(self) -> "Encounter":
        if self.period_end < self.period_start:
            raise ValueError("period_end must be on or after period_start")
        return self

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "encounter_type": "outpatient",
                "region_code": "US-CA",
                "period_start": "2025-01-01",
                "period_end": "2025-12-31",
                "aggregate_count": 248900,
            }
        },
    )


class IncidenceAggregate(ContractModel):
    disease_id: str = Field(min_length=1, max_length=64)
    disease_name: str = Field(min_length=1, max_length=160)
    region_code: str = Field(min_length=2, max_length=16, pattern=r"^[A-Z]{2}(-[A-Z0-9]{1,8})?$")
    year: int = Field(ge=1900, le=2100)
    incident_cases: int = Field(ge=0)
    population: int = Field(gt=0)
    incidence_per_100k: float = Field(ge=0)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "disease_id": "t2d",
                "disease_name": "Type 2 diabetes",
                "region_code": "US",
                "year": 2025,
                "incident_cases": 1540000,
                "population": 334900000,
                "incidence_per_100k": 459.8,
            }
        },
    )


class PrevalenceAggregate(ContractModel):
    disease_id: str = Field(min_length=1, max_length=64)
    disease_name: str = Field(min_length=1, max_length=160)
    region_code: str = Field(min_length=2, max_length=16, pattern=r"^[A-Z]{2}(-[A-Z0-9]{1,8})?$")
    year: int = Field(ge=1900, le=2100)
    prevalent_cases: int = Field(ge=0)
    population: int = Field(gt=0)
    prevalence_per_100k: float = Field(ge=0)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "disease_id": "t2d",
                "disease_name": "Type 2 diabetes",
                "region_code": "US",
                "year": 2025,
                "prevalent_cases": 32200000,
                "population": 334900000,
                "prevalence_per_100k": 9614.8,
            }
        },
    )


class MortalityAggregate(ContractModel):
    disease_id: str = Field(min_length=1, max_length=64)
    disease_name: str = Field(min_length=1, max_length=160)
    region_code: str = Field(min_length=2, max_length=16, pattern=r"^[A-Z]{2}(-[A-Z0-9]{1,8})?$")
    year: int = Field(ge=1900, le=2100)
    deaths: int = Field(ge=0)
    population: int = Field(gt=0)
    mortality_per_100k: float = Field(ge=0)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "disease_id": "t2d",
                "disease_name": "Type 2 diabetes",
                "region_code": "US",
                "year": 2025,
                "deaths": 27720,
                "population": 334900000,
                "mortality_per_100k": 8.3,
            }
        },
    )


class IndicationScore(ContractModel):
    indication_id: str = Field(min_length=1, max_length=64)
    indication_name: str = Field(min_length=1, max_length=160)
    incidence_score: float = Field(ge=0, le=100)
    unmet_need_score: float = Field(ge=0, le=100)
    market_size_score: float = Field(ge=0, le=100)
    competition_score: float = Field(ge=0, le=100)
    total_score: float = Field(ge=0, le=100)

    @field_validator(
        "incidence_score",
        "unmet_need_score",
        "market_size_score",
        "competition_score",
        "total_score",
        mode="before",
    )
    @classmethod
    def round_scores(cls, value: float) -> float:
        return round(float(value), 1)

    @model_validator(mode="after")
    def validate_total_score(self) -> "IndicationScore":
        expected = round(
            (
                self.incidence_score
                + self.unmet_need_score
                + self.market_size_score
                + self.competition_score
            )
            / 4,
            1,
        )
        if self.total_score != expected:
            raise ValueError("total_score must equal the average of the component scores")
        return self

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "indication_id": "t2d-us",
                "indication_name": "Type 2 diabetes",
                "incidence_score": 84.0,
                "unmet_need_score": 61.0,
                "market_size_score": 88.0,
                "competition_score": 42.0,
                "total_score": 68.8,
            }
        },
    )


class ScoringWeights(ContractModel):
    incidence: float = Field(default=0.24, ge=0, le=1)
    prevalence: float = Field(default=0.18, ge=0, le=1)
    unmet_need: float = Field(default=0.22, ge=0, le=1)
    market_size: float = Field(default=0.16, ge=0, le=1)
    competition_penalty: float = Field(default=0.12, ge=0, le=1)
    equity_score: float = Field(default=0.08, ge=0, le=1)

    @model_validator(mode="after")
    def validate_non_zero_weights(self) -> "ScoringWeights":
        total_weight = (
            self.incidence
            + self.prevalence
            + self.unmet_need
            + self.market_size
            + self.competition_penalty
            + self.equity_score
        )
        if total_weight <= 0:
            raise ValueError("at least one scoring weight must be greater than zero")
        return self

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "incidence": 0.24,
                "prevalence": 0.18,
                "unmet_need": 0.22,
                "market_size": 0.16,
                "competition_penalty": 0.12,
                "equity_score": 0.08,
            }
        },
    )


class FactorExplanation(ContractModel):
    factor: Literal[
        "incidence",
        "prevalence",
        "unmet_need",
        "market_size",
        "competition_penalty",
        "equity_score",
    ]
    raw_value: float = Field(ge=0, le=100)
    adjusted_score: float = Field(ge=0, le=100)
    weight: float = Field(ge=0, le=1)
    weighted_contribution: float = Field(ge=0, le=100)
    explanation: str = Field(min_length=1, max_length=280)
    evidence_classification: Literal["descriptive", "associative", "causal_hypothesis", "scenario_projection"] = "associative"
    caveat: str = Field(
        default="Contribution is associative and intended for prioritization support.",
        min_length=1,
        max_length=280,
    )


class RankedIndication(ContractModel):
    indication_id: str = Field(min_length=1, max_length=64)
    indication_name: str = Field(min_length=1, max_length=160)
    region_code: str = Field(min_length=2, max_length=16)
    total_score: float = Field(ge=0, le=100)
    weights_used: ScoringWeights
    explanations: list[FactorExplanation] = Field(min_length=6, max_length=6)
    summary: str = Field(min_length=1, max_length=400)
    scoring_profile_id: str = Field(default="default_v1", min_length=1, max_length=64)
    scoring_profile_version: str = Field(default="1.0.0", min_length=1, max_length=32)
    methodology_version: str = Field(default="score-v1.0", min_length=1, max_length=32)
    confidence_label: Literal["low", "medium", "high"] = "medium"
    result_classification: Literal["descriptive", "associative", "causal_hypothesis", "scenario_projection"] = "associative"
    input_provenance_summary: str = Field(
        default="Aggregate indication profile factors from tenant-scoped analytical store.",
        min_length=1,
        max_length=280,
    )
    data_limitations: list[str] = Field(
        default_factory=lambda: [
            "Scores are relative rankings over aggregate inputs, not prospective clinical outcomes."
        ],
        max_length=8,
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "indication_id": "t2d-us",
                "indication_name": "Type 2 diabetes",
                "region_code": "US",
                "total_score": 69.8,
                "weights_used": {
                    "incidence": 0.24,
                    "prevalence": 0.18,
                    "unmet_need": 0.22,
                    "market_size": 0.16,
                    "competition_penalty": 0.12,
                    "equity_score": 0.08,
                },
                "explanations": [
                    {
                        "factor": "incidence",
                        "raw_value": 84.0,
                        "adjusted_score": 84.0,
                        "weight": 0.24,
                        "weighted_contribution": 20.2,
                        "explanation": "Incidence contributes 20.2 points from a raw score of 84.0 at weight 0.24.",
                    },
                    {
                        "factor": "prevalence",
                        "raw_value": 78.0,
                        "adjusted_score": 78.0,
                        "weight": 0.18,
                        "weighted_contribution": 14.0,
                        "explanation": "Prevalence contributes 14.0 points from a raw score of 78.0 at weight 0.18.",
                    },
                    {
                        "factor": "unmet_need",
                        "raw_value": 61.0,
                        "adjusted_score": 61.0,
                        "weight": 0.22,
                        "weighted_contribution": 13.4,
                        "explanation": "Unmet need contributes 13.4 points from a raw score of 61.0 at weight 0.22.",
                    },
                    {
                        "factor": "market_size",
                        "raw_value": 88.0,
                        "adjusted_score": 88.0,
                        "weight": 0.16,
                        "weighted_contribution": 14.1,
                        "explanation": "Market size contributes 14.1 points from a raw score of 88.0 at weight 0.16.",
                    },
                    {
                        "factor": "competition_penalty",
                        "raw_value": 58.0,
                        "adjusted_score": 42.0,
                        "weight": 0.12,
                        "weighted_contribution": 5.0,
                        "explanation": "Competition penalty reduces attractiveness, so raw penalty 58.0 becomes adjusted score 42.0 and contributes 5.0 points.",
                    },
                    {
                        "factor": "equity_score",
                        "raw_value": 38.0,
                        "adjusted_score": 38.0,
                        "weight": 0.08,
                        "weighted_contribution": 3.0,
                        "explanation": "Equity score contributes 3.0 points from a raw score of 38.0 at weight 0.08.",
                    },
                ],
                "summary": "Type 2 diabetes ranks strongly on incidence, prevalence, and market size despite a moderate competition penalty.",
            }
        },
    )
