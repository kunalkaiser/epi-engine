from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
import json
from typing import Any

from apps.api.data import IndicationProfile
from apps.api.platform_models import SimulationResultItem
from apps.api.query_models import RankedIndicationsFilters
from apps.api.scoring import score_indication
from apps.api.contracts import ScoringWeights


@dataclass(frozen=True)
class SimulationExecutionResult:
    items: list[SimulationResultItem]
    summary: str


def run_scenario_engine(
    *,
    run_id: str,
    scenario_type: str,
    assumptions: dict[str, Any],
    baseline_profiles: list[IndicationProfile],
    region: str | None,
    limit: int,
) -> SimulationExecutionResult:
    filtered = [item for item in baseline_profiles if region is None or item.region_code == region]
    transformed = [_apply_scenario_transform(item, scenario_type, assumptions) for item in filtered]
    weights = _weights_from_assumptions(assumptions)
    baseline_weights = ScoringWeights()
    baseline_ranked = [score_indication(item, baseline_weights) for item in filtered]
    baseline_map = {item.indication_id: item.total_score for item in baseline_ranked}
    simulated_ranked = [score_indication(item, weights) for item in transformed]
    sorted_items = sorted(simulated_ranked, key=lambda item: (-item.total_score, item.indication_name))[:limit]

    confidence = float(assumptions.get("confidence_scale", 0.08))
    items: list[SimulationResultItem] = []
    for ranked in sorted_items:
        base_score = baseline_map.get(ranked.indication_id, ranked.total_score)
        low = max(0.0, round(ranked.total_score * (1 - confidence), 2))
        high = min(100.0, round(ranked.total_score * (1 + confidence), 2))
        items.append(
            SimulationResultItem(
                indication_id=ranked.indication_id,
                indication_name=ranked.indication_name,
                baseline_score=base_score,
                simulated_score=ranked.total_score,
                score_delta=round(ranked.total_score - base_score, 4),
                uncertainty_low=low,
                uncertainty_high=high,
                outcome_drivers=[exp.factor for exp in ranked.explanations[:3]],
                score_inputs={
                    "incidence": _get_profile_value(transformed, ranked.indication_id, "incidence"),
                    "prevalence": _get_profile_value(transformed, ranked.indication_id, "prevalence"),
                    "unmet_need": _get_profile_value(transformed, ranked.indication_id, "unmet_need"),
                    "market_size": _get_profile_value(transformed, ranked.indication_id, "market_size"),
                    "competition_penalty": _get_profile_value(transformed, ranked.indication_id, "competition_penalty"),
                    "equity_score": _get_profile_value(transformed, ranked.indication_id, "equity_score"),
                },
                trace_id=_build_trace_id(run_id, ranked.indication_id, assumptions),
                result_classification="scenario_projection",
                caveats=[
                    "Scenario projection is aggregate and non-causal.",
                    "Uncertainty bounds are sensitivity-based and depend on assumption quality.",
                ],
            )
        )

    return SimulationExecutionResult(
        items=items,
        summary=f"Scenario {scenario_type} produced {len(items)} aggregate-ranked indications.",
    )


def _apply_scenario_transform(
    profile: IndicationProfile, scenario_type: str, assumptions: dict[str, Any]
) -> IndicationProfile:
    incidence = profile.incidence
    prevalence = profile.prevalence
    unmet_need = profile.unmet_need
    market_size = profile.market_size
    competition_penalty = profile.competition_penalty
    equity_score = profile.equity_score

    if scenario_type == "subpopulation_targeting":
        incidence *= float(assumptions.get("subpopulation_incidence_multiplier", 1.15))
        unmet_need *= float(assumptions.get("subpopulation_unmet_need_multiplier", 1.1))
        equity_score *= float(assumptions.get("equity_focus_multiplier", 1.05))
    elif scenario_type == "regional_expansion":
        market_size *= float(assumptions.get("region_market_multiplier", 1.2))
        prevalence *= float(assumptions.get("region_prevalence_multiplier", 1.08))
        competition_penalty *= float(assumptions.get("region_competition_multiplier", 1.04))
    elif scenario_type == "trial_feasibility":
        feasibility = float(assumptions.get("feasibility_index", 0.6))
        unmet_need *= 1 + (1 - feasibility) * 0.2
        competition_penalty *= 1 - min(feasibility * 0.12, 0.2)
    elif scenario_type == "weighting_change":
        incidence *= float(assumptions.get("incidence_signal_multiplier", 1.0))
        prevalence *= float(assumptions.get("prevalence_signal_multiplier", 1.0))

    return IndicationProfile(
        indication_id=profile.indication_id,
        indication_name=profile.indication_name,
        region_code=profile.region_code,
        incidence=_clamp(incidence),
        prevalence=_clamp(prevalence),
        unmet_need=_clamp(unmet_need),
        market_size=_clamp(market_size),
        competition_penalty=_clamp(competition_penalty),
        equity_score=_clamp(equity_score),
    )


def _weights_from_assumptions(assumptions: dict[str, Any]) -> ScoringWeights:
    weights = assumptions.get("weights_override", {})
    if not isinstance(weights, dict):
        weights = {}
    return ScoringWeights(
        incidence=float(weights.get("incidence", 0.24)),
        prevalence=float(weights.get("prevalence", 0.18)),
        unmet_need=float(weights.get("unmet_need", 0.22)),
        market_size=float(weights.get("market_size", 0.16)),
        competition_penalty=float(weights.get("competition_penalty", 0.12)),
        equity_score=float(weights.get("equity_score", 0.08)),
    )


def _clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


def _get_profile_value(profiles: list[IndicationProfile], indication_id: str, field: str) -> float:
    for item in profiles:
        if item.indication_id == indication_id:
            return float(getattr(item, field))
    return 0.0


def _build_trace_id(run_id: str, indication_id: str, assumptions: dict[str, Any]) -> str:
    digest = sha1(
        json.dumps(
            {"run_id": run_id, "indication_id": indication_id, "assumptions": assumptions},
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:16]
    return f"trace_{digest}"
