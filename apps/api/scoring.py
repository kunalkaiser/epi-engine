from __future__ import annotations

from collections.abc import Iterable

from apps.api.contracts import FactorExplanation, RankedIndication, ScoringWeights
from apps.api.data import IndicationProfile


def rank_indications(
    profiles: Iterable[IndicationProfile],
    weights: ScoringWeights,
) -> list[RankedIndication]:
    ranked = [score_indication(profile, weights) for profile in profiles]
    return sorted(ranked, key=lambda item: (-item.total_score, item.indication_name))


def score_indication(profile: IndicationProfile, weights: ScoringWeights) -> RankedIndication:
    normalized_weights = _normalize_weights(weights)
    explanations = [
        _positive_factor("incidence", profile.incidence, normalized_weights.incidence),
        _positive_factor("prevalence", profile.prevalence, normalized_weights.prevalence),
        _positive_factor("unmet_need", profile.unmet_need, normalized_weights.unmet_need),
        _positive_factor("market_size", profile.market_size, normalized_weights.market_size),
        _competition_penalty(profile.competition_penalty, normalized_weights.competition_penalty),
        _positive_factor("equity_score", profile.equity_score, normalized_weights.equity_score),
    ]
    total_score = round(sum(item.weighted_contribution for item in explanations), 1)

    top_factors = sorted(
        explanations,
        key=lambda item: item.weighted_contribution,
        reverse=True,
    )[:3]
    summary = (
        f"{profile.indication_name} scores {total_score:.1f} with strongest weighted support from "
        f"{', '.join(item.factor for item in top_factors)}."
    )

    return RankedIndication(
        indication_id=profile.indication_id,
        indication_name=profile.indication_name,
        region_code=profile.region_code,
        total_score=total_score,
        weights_used=normalized_weights,
        explanations=explanations,
        summary=summary,
    )


def _normalize_weights(weights: ScoringWeights) -> ScoringWeights:
    total = (
        weights.incidence
        + weights.prevalence
        + weights.unmet_need
        + weights.market_size
        + weights.competition_penalty
        + weights.equity_score
    )
    return ScoringWeights(
        incidence=round(weights.incidence / total, 4),
        prevalence=round(weights.prevalence / total, 4),
        unmet_need=round(weights.unmet_need / total, 4),
        market_size=round(weights.market_size / total, 4),
        competition_penalty=round(weights.competition_penalty / total, 4),
        equity_score=round(weights.equity_score / total, 4),
    )


def _positive_factor(
    factor: str,
    raw_value: float,
    weight: float,
) -> FactorExplanation:
    adjusted_score = round(raw_value, 1)
    weighted_contribution = round(adjusted_score * weight, 1)
    label = factor.replace("_", " ")
    return FactorExplanation(
        factor=factor,
        raw_value=round(raw_value, 1),
        adjusted_score=adjusted_score,
        weight=round(weight, 4),
        weighted_contribution=weighted_contribution,
        explanation=(
            f"{label.capitalize()} contributes {weighted_contribution:.1f} points from a raw score of "
            f"{raw_value:.1f} at weight {weight:.2f}."
        ),
    )


def _competition_penalty(raw_value: float, weight: float) -> FactorExplanation:
    adjusted_score = round(100 - raw_value, 1)
    weighted_contribution = round(adjusted_score * weight, 1)
    return FactorExplanation(
        factor="competition_penalty",
        raw_value=round(raw_value, 1),
        adjusted_score=adjusted_score,
        weight=round(weight, 4),
        weighted_contribution=weighted_contribution,
        explanation=(
            "Competition penalty reduces attractiveness, so raw penalty "
            f"{raw_value:.1f} becomes adjusted score {adjusted_score:.1f} and contributes "
            f"{weighted_contribution:.1f} points."
        ),
    )
