from apps.api.contracts import ScoringWeights
from apps.api.data import INDICATION_PROFILES
from apps.api.scoring import rank_indications, score_indication


def test_score_indication_is_deterministic() -> None:
    weights = ScoringWeights(
        incidence=0.3,
        prevalence=0.2,
        unmet_need=0.2,
        market_size=0.1,
        competition_penalty=0.1,
        equity_score=0.1,
    )

    ranked = score_indication(INDICATION_PROFILES[0], weights)

    assert ranked.total_score == 69.8
    assert ranked.explanations[0].factor == "incidence"
    assert ranked.explanations[0].weighted_contribution == 25.2
    assert ranked.explanations[4].factor == "competition_penalty"
    assert ranked.explanations[4].adjusted_score == 42.0
    assert ranked.explanations[4].weighted_contribution == 4.2


def test_rank_indications_respects_weight_configuration() -> None:
    default_ranked = rank_indications(INDICATION_PROFILES, ScoringWeights())
    equity_heavy_ranked = rank_indications(
        INDICATION_PROFILES,
        ScoringWeights(
            incidence=0.05,
            prevalence=0.1,
            unmet_need=0.2,
            market_size=0.1,
            competition_penalty=0.1,
            equity_score=0.45,
        ),
    )

    assert default_ranked[0].indication_id == "t2d-us"
    assert equity_heavy_ranked[0].indication_id == "ckd-us-ca"


def test_ranked_indication_includes_transparency_metadata() -> None:
    ranked = rank_indications(INDICATION_PROFILES, ScoringWeights(), scoring_profile_id="default_v1", methodology_version="score-v1.1")

    assert ranked[0].scoring_profile_id == "default_v1"
    assert ranked[0].methodology_version == "score-v1.1"
    assert ranked[0].result_classification == "associative"
    assert ranked[0].confidence_label in {"low", "medium", "high"}
    assert ranked[0].explanations[0].evidence_classification in {
        "descriptive",
        "associative",
        "causal_hypothesis",
        "scenario_projection",
    }
