from pydantic import BaseModel, ConfigDict, Field

from apps.api.contracts import IncidenceAggregate, IndicationScore, PrevalenceAggregate


class IndicationProfile(BaseModel):
    indication_id: str = Field(min_length=1, max_length=64)
    indication_name: str = Field(min_length=1, max_length=160)
    region_code: str = Field(min_length=2, max_length=16)
    incidence: float = Field(ge=0, le=100)
    prevalence: float = Field(ge=0, le=100)
    unmet_need: float = Field(ge=0, le=100)
    market_size: float = Field(ge=0, le=100)
    competition_penalty: float = Field(ge=0, le=100)
    equity_score: float = Field(ge=0, le=100)

    model_config = ConfigDict(str_strip_whitespace=True)


INCIDENCE_DATA = [
    IncidenceAggregate(
        disease_id="t2d",
        disease_name="Type 2 diabetes",
        region_code="US",
        year=2024,
        incident_cases=1510000,
        population=333300000,
        incidence_per_100k=453.1,
    ),
    IncidenceAggregate(
        disease_id="t2d",
        disease_name="Type 2 diabetes",
        region_code="US",
        year=2025,
        incident_cases=1540000,
        population=334900000,
        incidence_per_100k=459.8,
    ),
    IncidenceAggregate(
        disease_id="copd",
        disease_name="Chronic obstructive pulmonary disease",
        region_code="US",
        year=2025,
        incident_cases=640000,
        population=334900000,
        incidence_per_100k=191.1,
    ),
    IncidenceAggregate(
        disease_id="t2d",
        disease_name="Type 2 diabetes",
        region_code="US-CA",
        year=2025,
        incident_cases=182000,
        population=39100000,
        incidence_per_100k=465.5,
    ),
]

PREVALENCE_DATA = [
    PrevalenceAggregate(
        disease_id="t2d",
        disease_name="Type 2 diabetes",
        region_code="US",
        year=2024,
        prevalent_cases=31600000,
        population=333300000,
        prevalence_per_100k=9480.9,
    ),
    PrevalenceAggregate(
        disease_id="t2d",
        disease_name="Type 2 diabetes",
        region_code="US",
        year=2025,
        prevalent_cases=32200000,
        population=334900000,
        prevalence_per_100k=9614.8,
    ),
    PrevalenceAggregate(
        disease_id="copd",
        disease_name="Chronic obstructive pulmonary disease",
        region_code="US",
        year=2025,
        prevalent_cases=16800000,
        population=334900000,
        prevalence_per_100k=5016.4,
    ),
    PrevalenceAggregate(
        disease_id="t2d",
        disease_name="Type 2 diabetes",
        region_code="US-CA",
        year=2025,
        prevalent_cases=3780000,
        population=39100000,
        prevalence_per_100k=9667.5,
    ),
]

INDICATION_SCORES = [
    IndicationScore(
        indication_id="t2d-us",
        indication_name="Type 2 diabetes",
        incidence_score=84.0,
        unmet_need_score=61.0,
        market_size_score=88.0,
        competition_score=42.0,
        total_score=68.8,
    ),
    IndicationScore(
        indication_id="copd-us",
        indication_name="Chronic obstructive pulmonary disease",
        incidence_score=67.0,
        unmet_need_score=74.0,
        market_size_score=72.0,
        competition_score=56.0,
        total_score=67.2,
    ),
    IndicationScore(
        indication_id="hf-us",
        indication_name="Heart failure",
        incidence_score=62.0,
        unmet_need_score=78.0,
        market_size_score=70.0,
        competition_score=58.0,
        total_score=67.0,
    ),
]

INDICATION_PROFILES = [
    IndicationProfile(
        indication_id="t2d-us",
        indication_name="Type 2 diabetes",
        region_code="US",
        incidence=84.0,
        prevalence=78.0,
        unmet_need=61.0,
        market_size=88.0,
        competition_penalty=58.0,
        equity_score=38.0,
    ),
    IndicationProfile(
        indication_id="copd-us",
        indication_name="Chronic obstructive pulmonary disease",
        region_code="US",
        incidence=67.0,
        prevalence=73.0,
        unmet_need=74.0,
        market_size=72.0,
        competition_penalty=44.0,
        equity_score=49.0,
    ),
    IndicationProfile(
        indication_id="hf-us",
        indication_name="Heart failure",
        region_code="US",
        incidence=62.0,
        prevalence=69.0,
        unmet_need=78.0,
        market_size=70.0,
        competition_penalty=42.0,
        equity_score=57.0,
    ),
    IndicationProfile(
        indication_id="ckd-us-ca",
        indication_name="Chronic kidney disease",
        region_code="US-CA",
        incidence=58.0,
        prevalence=71.0,
        unmet_need=76.0,
        market_size=66.0,
        competition_penalty=35.0,
        equity_score=64.0,
    ),
]
