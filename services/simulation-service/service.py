from __future__ import annotations

from apps.api.platform_models import (
    SimulationResultResponse,
    SimulationRunRequest,
    SimulationRunResponse,
)
from apps.api.platform_services import get_simulation_result, run_simulation


def run_scenario(payload: SimulationRunRequest) -> SimulationRunResponse:
    return run_simulation(payload)


def get_scenario_result(run_id: str) -> SimulationResultResponse | None:
    return get_simulation_result(run_id)
