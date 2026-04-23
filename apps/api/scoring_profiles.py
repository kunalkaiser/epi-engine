from __future__ import annotations

from dataclasses import dataclass

from apps.api.contracts import ScoringWeights


@dataclass(frozen=True)
class ScoringProfile:
    profile_id: str
    version: str
    name: str
    description: str
    assumptions: list[str]
    caveats: list[str]
    weights: ScoringWeights


SCORING_PROFILES: dict[str, ScoringProfile] = {
    "default_v1": ScoringProfile(
        profile_id="default_v1",
        version="1.0.0",
        name="Default Balanced",
        description="Balanced portfolio weighting for general indication prioritization.",
        assumptions=[
            "All factor inputs are aggregate-normalized to 0-100.",
            "Competition penalty is treated as inverse desirability.",
        ],
        caveats=[
            "Weights are heuristic and not market-forecast guarantees.",
            "Scores support prioritization discussion, not causal treatment efficacy conclusions.",
        ],
        weights=ScoringWeights(),
    ),
    "equity_focus_v1": ScoringProfile(
        profile_id="equity_focus_v1",
        version="1.0.0",
        name="Equity Focus",
        description="Increases equity and unmet need contribution for access-focused strategy.",
        assumptions=[
            "Equity inputs are available and quality-checked for target region.",
            "Unmet need proxies reflect current access gaps.",
        ],
        caveats=[
            "Equity signals may lag regional policy changes.",
            "Not a substitute for prospective health-economics evaluation.",
        ],
        weights=ScoringWeights(
            incidence=0.20,
            prevalence=0.16,
            unmet_need=0.24,
            market_size=0.12,
            competition_penalty=0.10,
            equity_score=0.18,
        ),
    ),
    "burden_focus_v1": ScoringProfile(
        profile_id="burden_focus_v1",
        version="1.0.0",
        name="Burden Focus",
        description="Prioritizes burden-heavy indications by incidence and prevalence.",
        assumptions=[
            "Burden metrics are consistent across compared indications.",
            "Market and competition are secondary in this policy.",
        ],
        caveats=[
            "May underweight commercially constrained indications.",
            "Useful for landscape triage; follow with deeper feasibility analysis.",
        ],
        weights=ScoringWeights(
            incidence=0.30,
            prevalence=0.24,
            unmet_need=0.18,
            market_size=0.12,
            competition_penalty=0.10,
            equity_score=0.06,
        ),
    ),
}


def get_scoring_profile(profile_id: str) -> ScoringProfile:
    profile = SCORING_PROFILES.get(profile_id)
    if profile is None:
        return SCORING_PROFILES["default_v1"]
    return profile


def list_scoring_profiles() -> list[ScoringProfile]:
    return list(SCORING_PROFILES.values())
