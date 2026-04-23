from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from apps.api.contracts import FactorExplanation, RankedIndication, ScoringWeights
from apps.api.data import IndicationProfile


def rank_indications(
    profiles: Iterable[IndicationProfile],
    weights: ScoringWeights,
    *,
    scoring_profile_id: str = "default_v1",
    scoring_profile_version: str = "1.0.0",
    methodology_version: str = "score-v1.0",
    profile_caveats: list[str] | None = None,
) -> list[RankedIndication]:
    ranked = [
        score_indication(
            profile,
            weights,
            scoring_profile_id=scoring_profile_id,
            scoring_profile_version=scoring_profile_version,
            methodology_version=methodology_version,
            profile_caveats=profile_caveats or [],
        )
        for profile in profiles
    ]
    return sorted(ranked, key=lambda item: (-item.total_score, item.indication_name))


def score_indication(
    profile: IndicationProfile,
    weights: ScoringWeights,
    *,
    scoring_profile_id: str = "default_v1",
    scoring_profile_version: str = "1.0.0",
    methodology_version: str = "score-v1.0",
    profile_caveats: list[str] | None = None,
) -> RankedIndication:
    normalized_weights = _normalize_weights(weights)
    explanations = [
        _positive_factor("incidence", profile.incidence, normalized_weights.incidence, "descriptive"),
        _positive_factor("prevalence", profile.prevalence, normalized_weights.prevalence, "descriptive"),
        _positive_factor("unmet_need", profile.unmet_need, normalized_weights.unmet_need, "associative"),
        _positive_factor("market_size", profile.market_size, normalized_weights.market_size, "associative"),
        _competition_penalty(profile.competition_penalty, normalized_weights.competition_penalty),
        _positive_factor("equity_score", profile.equity_score, normalized_weights.equity_score, "associative"),
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
        scoring_profile_id=scoring_profile_id,
        scoring_profile_version=scoring_profile_version,
        methodology_version=methodology_version,
        confidence_label=_confidence_label(explanations),
        result_classification="associative",
        input_provenance_summary="Aggregate incidence/prevalence/market/competition/equity inputs from tenant analytics store.",
        data_limitations=profile_caveats
        or [
            "Scores are ranking heuristics and should be combined with domain review.",
            "No patient-level causal effect estimation is performed in scoring.",
        ],
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
    classification: Literal["descriptive", "associative", "causal_hypothesis", "scenario_projection"],
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
        evidence_classification=classification,
        caveat="Factor contribution is aggregate and associative, not causal proof.",
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
        evidence_classification="associative",
        caveat="Competition proxy is directional and may not capture rapid market events.",
    )


def _confidence_label(explanations: list[FactorExplanation]) -> str:
    if not explanations:
        return "low"
    spread = max(item.weighted_contribution for item in explanations) - min(
        item.weighted_contribution for item in explanations
    )
    if spread >= 12:
        return "medium"
    if spread >= 6:
        return "high"
    return "low"
