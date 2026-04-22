from typing import Annotated

from fastapi import Query
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from pydantic import BaseModel, ConfigDict, Field, model_validator

from apps.api.contracts import ScoringWeights


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


class RankedIndicationsFilters(PaginationParams):
    region: str | None = Field(default=None, min_length=2, max_length=16)
    limit: int = Field(default=10, ge=1, le=100)
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


PaginationQuery = Annotated[PaginationParams, Query()]
RegionTimeQuery = Annotated[RegionTimeFilters, Query()]
TopIndicationsQuery = Annotated[TopIndicationsFilters, Query()]
RankedIndicationsQuery = Annotated[RankedIndicationsFilters, Query()]


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
) -> TopIndicationsFilters:
    return _validate_query_model(
        TopIndicationsFilters,
        page=page,
        page_size=page_size,
        region=region,
        year_from=year_from,
        year_to=year_to,
        limit=limit,
    )


def ranked_indications_filters_dependency(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    region: str | None = Query(default=None, min_length=2, max_length=16),
    limit: int = Query(default=10, ge=1, le=100),
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
        incidence_weight=incidence_weight,
        prevalence_weight=prevalence_weight,
        unmet_need_weight=unmet_need_weight,
        market_size_weight=market_size_weight,
        competition_penalty_weight=competition_penalty_weight,
        equity_score_weight=equity_score_weight,
    )


def _validate_query_model(model: type[PaginationParams], **data: int | str | None) -> PaginationParams:
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors(include_url=False)) from exc
