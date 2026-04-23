from apps.api.data import INDICATION_PROFILES
from apps.api.simulation_engine import run_scenario_engine


def test_simulation_engine_produces_uncertainty_and_traceability() -> None:
    result = run_scenario_engine(
        run_id="sim_test",
        scenario_type="subpopulation_targeting",
        assumptions={
            "subpopulation_incidence_multiplier": 1.2,
            "subpopulation_unmet_need_multiplier": 1.1,
            "weights_override": {"incidence": 0.3, "prevalence": 0.2, "unmet_need": 0.2, "market_size": 0.1, "competition_penalty": 0.1, "equity_score": 0.1},
            "confidence_scale": 0.1,
        },
        baseline_profiles=INDICATION_PROFILES,
        region="US",
        limit=2,
    )

    assert len(result.items) == 2
    first = result.items[0]
    assert first.uncertainty_low <= first.simulated_score <= first.uncertainty_high
    assert len(first.outcome_drivers) >= 1
    assert first.trace_id.startswith("trace_")
