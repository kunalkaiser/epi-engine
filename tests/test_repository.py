from apps.api.contracts import ScoringWeights
from apps.api.db import ClickHouseClient, ClickHouseConfig
from apps.api.query_models import PaginationParams, RankedIndicationsFilters, RegionTimeFilters
from apps.api.repository import ClickHouseAnalyticsRepository, SyntheticAnalyticsRepository
from apps.api.services import list_ranked_indications


class FakeClickHouseClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def query_json(self, sql, parameters=None):
        self.calls.append((sql, parameters or {}))
        return self.responses.pop(0)


def test_clickhouse_repository_builds_filtered_incidence_queries() -> None:
    client = FakeClickHouseClient(
        [
            [{"total_items": 1}],
            [
                {
                    "disease_id": "t2d",
                    "disease_name": "Type 2 diabetes",
                    "region_code": "US",
                    "year": 2025,
                    "incident_cases": 1540000,
                    "population": 334900000,
                    "incidence_per_100k": 459.8,
                }
            ],
        ]
    )
    repository = ClickHouseAnalyticsRepository(client)  # type: ignore[arg-type]

    result = repository.list_incidence(
        RegionTimeFilters(region="US", year_from=2025, year_to=2025, page=1, page_size=10)
    )

    assert result.pagination.total_items == 1
    assert result.items[0].disease_id == "t2d"
    assert "WHERE region_code = {region:String}" in client.calls[0][0]
    assert client.calls[0][1] == {"region": "US", "year_from": 2025, "year_to": 2025}


def test_clickhouse_repository_maps_ranked_profile_rows() -> None:
    client = FakeClickHouseClient(
        [
            [{"total_items": 2}],
            [
                {
                    "indication_id": "t2d-us",
                    "indication_name": "Type 2 diabetes",
                    "region_code": "US",
                    "incidence": 84.0,
                    "prevalence": 78.0,
                    "unmet_need": 61.0,
                    "market_size": 88.0,
                    "competition_penalty": 58.0,
                    "equity_score": 38.0,
                },
                {
                    "indication_id": "copd-us",
                    "indication_name": "Chronic obstructive pulmonary disease",
                    "region_code": "US",
                    "incidence": 67.0,
                    "prevalence": 73.0,
                    "unmet_need": 74.0,
                    "market_size": 72.0,
                    "competition_penalty": 44.0,
                    "equity_score": 49.0,
                },
            ],
        ]
    )
    repository = ClickHouseAnalyticsRepository(client)  # type: ignore[arg-type]

    result = repository.list_ranked_indication_profiles(
        RankedIndicationsFilters(region="US", limit=2, page=1, page_size=10)
    )

    assert result.pagination.total_items == 2
    assert result.items[0].indication_id == "t2d-us"


def test_clickhouse_repository_maps_mortality_rows() -> None:
    client = FakeClickHouseClient(
        [
            [{"total_items": 1}],
            [
                {
                    "disease_id": "t2d",
                    "disease_name": "Type 2 diabetes",
                    "region_code": "US",
                    "year": 2025,
                    "deaths": 27720,
                    "population": 334900000,
                    "mortality_per_100k": 8.3,
                }
            ],
        ]
    )
    repository = ClickHouseAnalyticsRepository(client)  # type: ignore[arg-type]

    result = repository.list_mortality(
        RegionTimeFilters(region="US", year_from=2025, year_to=2025, page=1, page_size=10)
    )

    assert result.pagination.total_items == 1
    assert result.items[0].deaths == 27720
    assert "FROM mortality_facts" in client.calls[0][0]


def test_ranked_service_works_with_synthetic_repository_adapter() -> None:
    repository = SyntheticAnalyticsRepository()

    response = list_ranked_indications(
        RankedIndicationsFilters(
            region="US",
            limit=2,
            page=1,
            page_size=10,
            incidence_weight=0.3,
            prevalence_weight=0.2,
            unmet_need_weight=0.2,
            market_size_weight=0.1,
            competition_penalty_weight=0.1,
            equity_score_weight=0.1,
        ),
        repository=repository,
    )

    assert response.pagination.total_items == 2
    assert response.items[0].indication_id == "t2d-us"


def test_ranked_service_uses_clickhouse_rows_when_repository_provided() -> None:
    client = FakeClickHouseClient(
        [
            [{"total_items": 1}],
            [
                {
                    "indication_id": "rare-us",
                    "indication_name": "Rare indication",
                    "region_code": "US",
                    "incidence": 22.0,
                    "prevalence": 17.0,
                    "unmet_need": 95.0,
                    "market_size": 35.0,
                    "competition_penalty": 8.0,
                    "equity_score": 77.0,
                }
            ],
        ]
    )
    repository = ClickHouseAnalyticsRepository(client)  # type: ignore[arg-type]

    response = list_ranked_indications(
        RankedIndicationsFilters(region="US", limit=5, page=1, page_size=10),
        repository=repository,
    )

    assert response.pagination.total_items == 1
    assert response.items[0].indication_id == "rare-us"


def test_synthetic_repository_derives_mortality_for_dev_fallback() -> None:
    repository = SyntheticAnalyticsRepository()

    result = repository.list_mortality(RegionTimeFilters(region="US", page=1, page_size=5))

    assert result.pagination.total_items >= 1
    assert result.items[0].deaths >= 0
