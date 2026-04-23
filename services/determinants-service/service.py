from __future__ import annotations

from apps.api.platform_models import DeterminantsResponse
from apps.api.platform_services import get_determinants
from apps.api.query_models import RegionTimeFilters


def run_determinants_analysis(filters: RegionTimeFilters) -> DeterminantsResponse:
    return get_determinants(filters)
