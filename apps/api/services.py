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
from apps.api.scoring_profiles import ScoringProfile, get_scoring_profile
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
    profile = get_scoring_profile(filters.profile_id)
    profiles_result = repository.list_ranked_indication_profiles(
        RankedIndicationsFilters(
            region=filters.region,
            limit=filters.limit,
            page=1,
            page_size=filters.limit,
            profile_id=profile.profile_id,
            incidence_weight=profile.weights.incidence,
            prevalence_weight=profile.weights.prevalence,
            unmet_need_weight=profile.weights.unmet_need,
            market_size_weight=profile.weights.market_size,
            competition_penalty_weight=profile.weights.competition_penalty,
            equity_score_weight=profile.weights.equity_score,
        )
    )
    ranked_items = rank_indications(
        profiles_result.items,
        profile.weights,
        scoring_profile_id=profile.profile_id,
        scoring_profile_version=profile.version,
        methodology_version="score-v1.1",
        profile_caveats=profile.caveats,
    )
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
    pagination = _build_pagination(page=filters.page, page_size=filters.page_size, total_items=total_items)
    return TopIndicationsResponse(
        items=paged,
        pagination=pagination,
        scoring_profile=_scoring_profile_payload(profile, include_details=False),
        methodology=_scoring_methodology_payload(limitations=profile.caveats),
    )


def list_ranked_indications(filters: RankedIndicationsFilters, repository: AnalyticsRepository | None = None) -> RankedIndicationsResponse:
    repository = repository or build_analytics_repository()
    profile = get_scoring_profile(filters.profile_id)
    effective_weights = filters.to_scoring_weights() if filters.has_custom_weight_overrides() else profile.weights
    profiles_result = repository.list_ranked_indication_profiles(filters)
    ranked_items = rank_indications(
        profiles_result.items,
        effective_weights,
        scoring_profile_id=profile.profile_id,
        scoring_profile_version=profile.version,
        methodology_version="score-v1.1",
        profile_caveats=profile.caveats,
    )[: filters.limit]
    start = (filters.page - 1) * filters.page_size
    end = start + filters.page_size
    total_items = min(profiles_result.pagination.total_items, filters.limit)
    pagination = _build_pagination(page=filters.page, page_size=filters.page_size, total_items=total_items)
    page_items = ranked_items[start:end]
    return RankedIndicationsResponse(
        items=page_items,
        pagination=pagination,
        scoring_profile=_scoring_profile_payload(profile, include_details=True),
        methodology=_scoring_methodology_payload(),
        caveats=profile.caveats,
    )


def _build_pagination(*, page: int, page_size: int, total_items: int) -> dict[str, int]:
    total_pages = (total_items + page_size - 1) // page_size if total_items else 0
    return {
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
    }


def _scoring_profile_payload(profile: ScoringProfile, *, include_details: bool) -> dict[str, object]:
    payload: dict[str, object] = {
        "profile_id": profile.profile_id,
        "version": profile.version,
        "name": profile.name,
    }
    if include_details:
        payload["description"] = profile.description
        payload["assumptions"] = profile.assumptions
    return payload


def _scoring_methodology_payload(*, limitations: list[str] | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "result_classification": "associative",
        "methodology_version": "score-v1.1",
        "uncertainty_semantics": "Relative ranking confidence from weighted contribution dispersion.",
    }
    if limitations is not None:
        payload["limitations"] = limitations
    return payload
