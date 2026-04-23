from __future__ import annotations

from apps.api.query_models import PaginationParams, RegionTimeFilters
from apps.api.response_models import DiseasesResponse, IncidenceResponse, PrevalenceResponse
from apps.api.services import list_diseases, list_incidence, list_prevalence


def get_disease_catalog(params: PaginationParams) -> DiseasesResponse:
    return list_diseases(params)


def get_incidence(filters: RegionTimeFilters) -> IncidenceResponse:
    return list_incidence(filters)


def get_prevalence(filters: RegionTimeFilters) -> PrevalenceResponse:
    return list_prevalence(filters)
