from typing import Annotated, TypeVar
from datetime import date

from fastapi import Query
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from pydantic import BaseModel, ConfigDict, Field, model_validator

from apps.api.contracts import ScoringWeights

ModelT = TypeVar("ModelT", bound=BaseModel)


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    model_config = ConfigDict(extra="forbid")


class RegionTimeFilters(PaginationParams):
    region: str | None = Field(default=None, min_length=2, max_length=16)
    year_from: int | None = Field(default=None, ge=1900, le=2100)
    year_to: int | None = Field(default=None, ge=1900, le=2100)

    @model_validator(mode="after")
    def validate_years(self) -> "RegionTimeFilters":
        if self.year_from is not None and self.year_to is not None and self.year_to < self.year_from:
            raise ValueError("year_to must be greater than or equal to year_from")
        return self


class TopIndicationsFilters(RegionTimeFilters):
    limit: int = Field(default=10, ge=1, le=100)
    profile_id: str = Field(default="default_v1", min_length=1, max_length=64)


class RankedIndicationsFilters(PaginationParams):
    region: str | None = Field(default=None, min_length=2, max_length=16)
    limit: int = Field(default=10, ge=1, le=100)
    profile_id: str = Field(default="default_v1", min_length=1, max_length=64)
    incidence_weight: float = Field(default=0.24, ge=0, le=1)
    prevalence_weight: float = Field(default=0.18, ge=0, le=1)
    unmet_need_weight: float = Field(default=0.22, ge=0, le=1)
    market_size_weight: float = Field(default=0.16, ge=0, le=1)
    competition_penalty_weight: float = Field(default=0.12, ge=0, le=1)
    equity_score_weight: float = Field(default=0.08, ge=0, le=1)

    def to_scoring_weights(self) -> ScoringWeights:
        return ScoringWeights(
            incidence=self.incidence_weight,
            prevalence=self.prevalence_weight,
            unmet_need=self.unmet_need_weight,
            market_size=self.market_size_weight,
            competition_penalty=self.competition_penalty_weight,
            equity_score=self.equity_score_weight,
        )

    def has_custom_weight_overrides(self) -> bool:
        return any(
            [
                self.incidence_weight != 0.24,
                self.prevalence_weight != 0.18,
                self.unmet_need_weight != 0.22,
                self.market_size_weight != 0.16,
                self.competition_penalty_weight != 0.12,
                self.equity_score_weight != 0.08,
            ]
        )


class SimulationRunsFilters(PaginationParams):
    status: str | None = None
    scenario_type: str | None = None


class IngestionRunsFilters(PaginationParams):
    source_system: str | None = None
    status: str | None = None
    trigger_source: str | None = None
    date_from: date | None = None
    date_to: date | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "IngestionRunsFilters":
        if self.date_from and self.date_to and self.date_to < self.date_from:
            raise ValueError("date_to must be greater than or equal to date_from")
        return self


class DataQualityRunsFilters(PaginationParams):
    domain: str | None = None
    status: str | None = None
    severity: str | None = None
    date_from: date | None = None
    date_to: date | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "DataQualityRunsFilters":
        if self.date_from and self.date_to and self.date_to < self.date_from:
            raise ValueError("date_to must be greater than or equal to date_from")
        return self


PaginationQuery = Annotated[PaginationParams, Query()]
RegionTimeQuery = Annotated[RegionTimeFilters, Query()]
TopIndicationsQuery = Annotated[TopIndicationsFilters, Query()]
RankedIndicationsQuery = Annotated[RankedIndicationsFilters, Query()]
SimulationRunsQuery = Annotated[SimulationRunsFilters, Query()]
IngestionRunsQuery = Annotated[IngestionRunsFilters, Query()]
DataQualityRunsQuery = Annotated[DataQualityRunsFilters, Query()]


def pagination_params_dependency(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginationParams:
    return _validate_query_model(PaginationParams, page=page, page_size=page_size)


def region_time_filters_dependency(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    region: str | None = Query(default=None, min_length=2, max_length=16),
    year_from: int | None = Query(default=None, ge=1900, le=2100),
    year_to: int | None = Query(default=None, ge=1900, le=2100),
) -> RegionTimeFilters:
    return _validate_query_model(
        RegionTimeFilters,
        page=page,
        page_size=page_size,
        region=region,
        year_from=year_from,
        year_to=year_to,
    )


def top_indications_filters_dependency(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    region: str | None = Query(default=None, min_length=2, max_length=16),
    year_from: int | None = Query(default=None, ge=1900, le=2100),
    year_to: int | None = Query(default=None, ge=1900, le=2100),
    limit: int = Query(default=10, ge=1, le=100),
    profile_id: str = Query(default="default_v1", min_length=1, max_length=64),
) -> TopIndicationsFilters:
    return _validate_query_model(
        TopIndicationsFilters,
        page=page,
        page_size=page_size,
        region=region,
        year_from=year_from,
        year_to=year_to,
        limit=limit,
        profile_id=profile_id,
    )


def ranked_indications_filters_dependency(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    region: str | None = Query(default=None, min_length=2, max_length=16),
    limit: int = Query(default=10, ge=1, le=100),
    profile_id: str = Query(default="default_v1", min_length=1, max_length=64),
    incidence_weight: float = Query(default=0.24, ge=0, le=1),
    prevalence_weight: float = Query(default=0.18, ge=0, le=1),
    unmet_need_weight: float = Query(default=0.22, ge=0, le=1),
    market_size_weight: float = Query(default=0.16, ge=0, le=1),
    competition_penalty_weight: float = Query(default=0.12, ge=0, le=1),
    equity_score_weight: float = Query(default=0.08, ge=0, le=1),
) -> RankedIndicationsFilters:
    return _validate_query_model(
        RankedIndicationsFilters,
        page=page,
        page_size=page_size,
        region=region,
        limit=limit,
        profile_id=profile_id,
        incidence_weight=incidence_weight,
        prevalence_weight=prevalence_weight,
        unmet_need_weight=unmet_need_weight,
        market_size_weight=market_size_weight,
        competition_penalty_weight=competition_penalty_weight,
        equity_score_weight=equity_score_weight,
    )


def simulation_runs_filters_dependency(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    scenario_type: str | None = Query(default=None),
) -> SimulationRunsFilters:
    return _validate_query_model(
        SimulationRunsFilters,
        page=page,
        page_size=page_size,
        status=status,
        scenario_type=scenario_type,
    )


def ingestion_runs_filters_dependency(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    source_system: str | None = Query(default=None),
    status: str | None = Query(default=None),
    trigger_source: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> IngestionRunsFilters:
    return _validate_query_model(
        IngestionRunsFilters,
        page=page,
        page_size=page_size,
        source_system=source_system,
        status=status,
        trigger_source=trigger_source,
        date_from=date_from,
        date_to=date_to,
    )


def data_quality_runs_filters_dependency(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    domain: str | None = Query(default=None),
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> DataQualityRunsFilters:
    return _validate_query_model(
        DataQualityRunsFilters,
        page=page,
        page_size=page_size,
        domain=domain,
        status=status,
        severity=severity,
        date_from=date_from,
        date_to=date_to,
    )


def _validate_query_model(model: type[ModelT], **data: int | str | date | None) -> ModelT:
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors(include_url=False)) from exc
ModelT = TypeVar("ModelT", bound=BaseModel)
