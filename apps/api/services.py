from apps.api.contracts import IndicationScore
from apps.api.query_models import PaginationParams, RankedIndicationsFilters, RegionTimeFilters, TopIndicationsFilters
from apps.api.response_models import (
    DiseasesResponse,
    IncidenceResponse,
    PrevalenceResponse,
    RankedIndicationsResponse,
    TopIndicationsResponse,
)
from apps.api.repository import AnalyticsRepository, build_analytics_repository
from apps.api.scoring import rank_indications


def list_diseases(params: PaginationParams, repository: AnalyticsRepository | None = None) -> DiseasesResponse:
    repository = repository or build_analytics_repository()
    result = repository.list_diseases(params)
    return DiseasesResponse(items=result.items, pagination=result.pagination)


def list_incidence(filters: RegionTimeFilters, repository: AnalyticsRepository | None = None) -> IncidenceResponse:
    repository = repository or build_analytics_repository()
    result = repository.list_incidence(filters)
    return IncidenceResponse(items=result.items, pagination=result.pagination)


def list_prevalence(filters: RegionTimeFilters, repository: AnalyticsRepository | None = None) -> PrevalenceResponse:
    repository = repository or build_analytics_repository()
    result = repository.list_prevalence(filters)
    return PrevalenceResponse(items=result.items, pagination=result.pagination)


def list_top_indications(filters: TopIndicationsFilters) -> TopIndicationsResponse:
    repository = build_analytics_repository()
    profiles_result = repository.list_ranked_indication_profiles(
        RankedIndicationsFilters(
            region=filters.region,
            limit=filters.limit,
            page=1,
            page_size=filters.limit,
            incidence_weight=0.24,
            prevalence_weight=0.18,
            unmet_need_weight=0.22,
            market_size_weight=0.16,
            competition_penalty_weight=0.12,
            equity_score_weight=0.08,
        )
    )
    ranked_items = rank_indications(profiles_result.items, RankedIndicationsFilters().to_scoring_weights())
    top_items = [
        IndicationScore(
            indication_id=item.indication_id,
            indication_name=item.indication_name,
            incidence_score=item.explanations[0].adjusted_score,
            unmet_need_score=item.explanations[2].adjusted_score,
            market_size_score=item.explanations[3].adjusted_score,
            competition_score=item.explanations[4].adjusted_score,
            total_score=round(
                (
                    item.explanations[0].adjusted_score
                    + item.explanations[2].adjusted_score
                    + item.explanations[3].adjusted_score
                    + item.explanations[4].adjusted_score
                )
                / 4,
                1,
            ),
        )
        for item in ranked_items[: filters.limit]
    ]
    start = (filters.page - 1) * filters.page_size
    end = start + filters.page_size
    paged = top_items[start:end]
    total_items = len(top_items)
    total_pages = (total_items + filters.page_size - 1) // filters.page_size if total_items else 0
    return TopIndicationsResponse(
        items=paged,
        pagination={
            "page": filters.page,
            "page_size": filters.page_size,
            "total_items": total_items,
            "total_pages": total_pages,
        },
    )


def list_ranked_indications(filters: RankedIndicationsFilters, repository: AnalyticsRepository | None = None) -> RankedIndicationsResponse:
    repository = repository or build_analytics_repository()
    profiles_result = repository.list_ranked_indication_profiles(filters)
    ranked_items = rank_indications(profiles_result.items, filters.to_scoring_weights())[: filters.limit]
    start = (filters.page - 1) * filters.page_size
    end = start + filters.page_size
    total_items = min(profiles_result.pagination.total_items, filters.limit)
    total_pages = (total_items + filters.page_size - 1) // filters.page_size if total_items else 0
    page_items = ranked_items[start:end]
    return RankedIndicationsResponse(
        items=page_items,
        pagination={
            "page": filters.page,
            "page_size": filters.page_size,
            "total_items": total_items,
            "total_pages": total_pages,
        },
    )
