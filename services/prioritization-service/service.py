from __future__ import annotations

from apps.api.query_models import RankedIndicationsFilters, TopIndicationsFilters
from apps.api.response_models import RankedIndicationsResponse, TopIndicationsResponse
from apps.api.services import list_ranked_indications, list_top_indications


def get_top_indications(filters: TopIndicationsFilters) -> TopIndicationsResponse:
    return list_top_indications(filters)


def get_ranked_indications(filters: RankedIndicationsFilters) -> RankedIndicationsResponse:
    return list_ranked_indications(filters)
