from __future__ import annotations

from dataclasses import dataclass
import logging
from math import ceil
from typing import Protocol

from apps.api.contracts import IncidenceAggregate, MortalityAggregate, PrevalenceAggregate
from apps.api.data import INCIDENCE_DATA, INDICATION_PROFILES, PREVALENCE_DATA, IndicationProfile
from apps.api.db import ClickHouseClient, ClickHouseConfig, ClickHouseUnavailableError
from apps.api.logging_utils import get_logger, log_event
from apps.api.pg import PostgresClient, PostgresConfig
from apps.api.query_models import PaginationParams, RankedIndicationsFilters, RegionTimeFilters
from apps.api.response_models import DiseaseListItem, PaginationMeta
from apps.api.settings import get_settings


logger = get_logger("epi_engine.api.repository")


@dataclass(frozen=True)
class PaginatedResult:
    items: list
    pagination: PaginationMeta


class AnalyticsRepository(Protocol):
    def list_diseases(self, params: PaginationParams) -> PaginatedResult:
        ...

    def list_incidence(self, filters: RegionTimeFilters) -> PaginatedResult:
        ...

    def list_prevalence(self, filters: RegionTimeFilters) -> PaginatedResult:
        ...

    def list_mortality(self, filters: RegionTimeFilters) -> PaginatedResult:
        ...

    def list_ranked_indication_profiles(self, filters: RankedIndicationsFilters) -> PaginatedResult:
        ...


class ClickHouseAnalyticsRepository:
    def __init__(self, client: ClickHouseClient) -> None:
        self.client = client

    def list_diseases(self, params: PaginationParams) -> PaginatedResult:
        count_rows = self.client.query_json(
            """
            SELECT count() AS total_items
            FROM
            (
                SELECT disease_id
                FROM incidence_facts
                UNION DISTINCT
                SELECT disease_id
                FROM prevalence_facts
            )
            """
        )
        total_items = int(count_rows[0]["total_items"]) if count_rows else 0
        offset = (params.page - 1) * params.page_size

        rows = self.client.query_json(
            """
            SELECT
                disease_id,
                any(disease_name) AS disease_name,
                arraySort(arrayDistinct(groupArray(region_code))) AS regions,
                min(metric_year) AS year_min,
                max(metric_year) AS year_max
            FROM
            (
                SELECT disease_id, disease_name, region_code, metric_year
                FROM incidence_facts
                UNION ALL
                SELECT disease_id, disease_name, region_code, metric_year
                FROM prevalence_facts
            )
            GROUP BY disease_id
            ORDER BY disease_name ASC
            LIMIT {limit:UInt64} OFFSET {offset:UInt64}
            """,
            {"limit": params.page_size, "offset": offset},
        )
        items = [
            DiseaseListItem(
                disease_id=row["disease_id"],
                disease_name=row["disease_name"],
                regions=row["regions"],
                year_min=int(row["year_min"]),
                year_max=int(row["year_max"]),
            )
            for row in rows
        ]
        return PaginatedResult(items=items, pagination=_build_pagination(params.page, params.page_size, total_items))

    def list_incidence(self, filters: RegionTimeFilters) -> PaginatedResult:
        where_clause, query_params = _build_region_time_where(filters, "metric_year", "region_code")
        count_rows = self.client.query_json(
            f"SELECT count() AS total_items FROM incidence_facts {where_clause}",
            query_params,
        )
        total_items = int(count_rows[0]["total_items"]) if count_rows else 0
        offset = (filters.page - 1) * filters.page_size
        rows = self.client.query_json(
            f"""
            SELECT
                disease_id,
                disease_name,
                region_code,
                metric_year AS year,
                incident_cases,
                population,
                incidence_per_100k
            FROM incidence_facts
            {where_clause}
            ORDER BY year DESC, disease_name DESC, region_code DESC
            LIMIT {{limit:UInt64}} OFFSET {{offset:UInt64}}
            """,
            {**query_params, "limit": filters.page_size, "offset": offset},
        )
        items = [
            IncidenceAggregate(
                disease_id=row["disease_id"],
                disease_name=row["disease_name"],
                region_code=row["region_code"],
                year=int(row["year"]),
                incident_cases=int(row["incident_cases"]),
                population=int(row["population"]),
                incidence_per_100k=float(row["incidence_per_100k"]),
            )
            for row in rows
        ]
        return PaginatedResult(items=items, pagination=_build_pagination(filters.page, filters.page_size, total_items))

    def list_prevalence(self, filters: RegionTimeFilters) -> PaginatedResult:
        where_clause, query_params = _build_region_time_where(filters, "metric_year", "region_code")
        count_rows = self.client.query_json(
            f"SELECT count() AS total_items FROM prevalence_facts {where_clause}",
            query_params,
        )
        total_items = int(count_rows[0]["total_items"]) if count_rows else 0
        offset = (filters.page - 1) * filters.page_size
        rows = self.client.query_json(
            f"""
            SELECT
                disease_id,
                disease_name,
                region_code,
                metric_year AS year,
                prevalent_cases,
                population,
                prevalence_per_100k
            FROM prevalence_facts
            {where_clause}
            ORDER BY year DESC, disease_name DESC, region_code DESC
            LIMIT {{limit:UInt64}} OFFSET {{offset:UInt64}}
            """,
            {**query_params, "limit": filters.page_size, "offset": offset},
        )
        items = [
            PrevalenceAggregate(
                disease_id=row["disease_id"],
                disease_name=row["disease_name"],
                region_code=row["region_code"],
                year=int(row["year"]),
                prevalent_cases=int(row["prevalent_cases"]),
                population=int(row["population"]),
                prevalence_per_100k=float(row["prevalence_per_100k"]),
            )
            for row in rows
        ]
        return PaginatedResult(items=items, pagination=_build_pagination(filters.page, filters.page_size, total_items))

    def list_mortality(self, filters: RegionTimeFilters) -> PaginatedResult:
        where_clause, query_params = _build_region_time_where(filters, "metric_year", "region_code")
        count_rows = self.client.query_json(
            f"SELECT count() AS total_items FROM mortality_facts {where_clause}",
            query_params,
        )
        total_items = int(count_rows[0]["total_items"]) if count_rows else 0
        offset = (filters.page - 1) * filters.page_size
        rows = self.client.query_json(
            f"""
            SELECT
                disease_id,
                disease_name,
                region_code,
                metric_year AS year,
                deaths,
                population,
                mortality_per_100k
            FROM mortality_facts
            {where_clause}
            ORDER BY year DESC, disease_name DESC, region_code DESC
            LIMIT {{limit:UInt64}} OFFSET {{offset:UInt64}}
            """,
            {**query_params, "limit": filters.page_size, "offset": offset},
        )
        items = [
            MortalityAggregate(
                disease_id=row["disease_id"],
                disease_name=row["disease_name"],
                region_code=row["region_code"],
                year=int(row["year"]),
                deaths=int(row["deaths"]),
                population=int(row["population"]),
                mortality_per_100k=float(row["mortality_per_100k"]),
            )
            for row in rows
        ]
        return PaginatedResult(items=items, pagination=_build_pagination(filters.page, filters.page_size, total_items))

    def list_ranked_indication_profiles(self, filters: RankedIndicationsFilters) -> PaginatedResult:
        where_parts: list[str] = []
        query_params: dict[str, object] = {}
        if filters.region is not None:
            where_parts.append("region_code = {region:String}")
            query_params["region"] = filters.region
        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

        count_rows = self.client.query_json(
            f"SELECT count() AS total_items FROM indication_profile_facts {where_clause}",
            query_params,
        )
        total_items = min(int(count_rows[0]["total_items"]) if count_rows else 0, filters.limit)
        rows = self.client.query_json(
            f"""
            SELECT
                indication_id,
                indication_name,
                region_code,
                incidence,
                prevalence,
                unmet_need,
                market_size,
                competition_penalty,
                equity_score
            FROM indication_profile_facts
            {where_clause}
            ORDER BY indication_name ASC
            LIMIT {{limit:UInt64}}
            """,
            {**query_params, "limit": filters.limit},
        )
        items = [
            IndicationProfile(
                indication_id=row["indication_id"],
                indication_name=row["indication_name"],
                region_code=row["region_code"],
                incidence=float(row["incidence"]),
                prevalence=float(row["prevalence"]),
                unmet_need=float(row["unmet_need"]),
                market_size=float(row["market_size"]),
                competition_penalty=float(row["competition_penalty"]),
                equity_score=float(row["equity_score"]),
            )
            for row in rows
        ]
        page_items, pagination = _paginate(items, filters.page, filters.page_size, total_items_override=total_items)
        return PaginatedResult(items=page_items, pagination=pagination)


class PostgresAnalyticsRepository:
    """Postgres/Supabase read-path repository. Mirrors ClickHouseAnalyticsRepository
    but in Postgres dialect: count(*) instead of count(), aliased derived tables,
    and array_agg(DISTINCT ... ORDER BY) / min() in place of the ClickHouse
    groupArray/any helpers. {name:Type} placeholders are translated to %(name)s by
    PostgresClient, so the shared WHERE/param helpers below work unchanged.
    """

    def __init__(self, client: PostgresClient) -> None:
        self.client = client

    def list_diseases(self, params: PaginationParams) -> PaginatedResult:
        count_rows = self.client.query_json(
            """
            SELECT count(*) AS total_items
            FROM
            (
                SELECT disease_id FROM incidence_facts
                UNION
                SELECT disease_id FROM prevalence_facts
            ) AS distinct_diseases
            """
        )
        total_items = int(count_rows[0]["total_items"]) if count_rows else 0
        offset = (params.page - 1) * params.page_size

        rows = self.client.query_json(
            """
            SELECT
                disease_id,
                min(disease_name) AS disease_name,
                array_agg(DISTINCT region_code ORDER BY region_code) AS regions,
                min(metric_year) AS year_min,
                max(metric_year) AS year_max
            FROM
            (
                SELECT disease_id, disease_name, region_code, metric_year
                FROM incidence_facts
                UNION ALL
                SELECT disease_id, disease_name, region_code, metric_year
                FROM prevalence_facts
            ) AS disease_years
            GROUP BY disease_id
            ORDER BY disease_name ASC
            LIMIT {limit:UInt64} OFFSET {offset:UInt64}
            """,
            {"limit": params.page_size, "offset": offset},
        )
        items = [
            DiseaseListItem(
                disease_id=row["disease_id"],
                disease_name=row["disease_name"],
                regions=list(row["regions"]),
                year_min=int(row["year_min"]),
                year_max=int(row["year_max"]),
            )
            for row in rows
        ]
        return PaginatedResult(items=items, pagination=_build_pagination(params.page, params.page_size, total_items))

    def list_incidence(self, filters: RegionTimeFilters) -> PaginatedResult:
        where_clause, query_params = _build_region_time_where(filters, "metric_year", "region_code")
        count_rows = self.client.query_json(
            f"SELECT count(*) AS total_items FROM incidence_facts {where_clause}",
            query_params,
        )
        total_items = int(count_rows[0]["total_items"]) if count_rows else 0
        offset = (filters.page - 1) * filters.page_size
        rows = self.client.query_json(
            f"""
            SELECT
                disease_id,
                disease_name,
                region_code,
                metric_year AS year,
                incident_cases,
                population,
                incidence_per_100k
            FROM incidence_facts
            {where_clause}
            ORDER BY year DESC, disease_name DESC, region_code DESC
            LIMIT {{limit:UInt64}} OFFSET {{offset:UInt64}}
            """,
            {**query_params, "limit": filters.page_size, "offset": offset},
        )
        items = [
            IncidenceAggregate(
                disease_id=row["disease_id"],
                disease_name=row["disease_name"],
                region_code=row["region_code"],
                year=int(row["year"]),
                incident_cases=int(row["incident_cases"]),
                population=int(row["population"]),
                incidence_per_100k=float(row["incidence_per_100k"]),
            )
            for row in rows
        ]
        return PaginatedResult(items=items, pagination=_build_pagination(filters.page, filters.page_size, total_items))

    def list_prevalence(self, filters: RegionTimeFilters) -> PaginatedResult:
        where_clause, query_params = _build_region_time_where(filters, "metric_year", "region_code")
        count_rows = self.client.query_json(
            f"SELECT count(*) AS total_items FROM prevalence_facts {where_clause}",
            query_params,
        )
        total_items = int(count_rows[0]["total_items"]) if count_rows else 0
        offset = (filters.page - 1) * filters.page_size
        rows = self.client.query_json(
            f"""
            SELECT
                disease_id,
                disease_name,
                region_code,
                metric_year AS year,
                prevalent_cases,
                population,
                prevalence_per_100k
            FROM prevalence_facts
            {where_clause}
            ORDER BY year DESC, disease_name DESC, region_code DESC
            LIMIT {{limit:UInt64}} OFFSET {{offset:UInt64}}
            """,
            {**query_params, "limit": filters.page_size, "offset": offset},
        )
        items = [
            PrevalenceAggregate(
                disease_id=row["disease_id"],
                disease_name=row["disease_name"],
                region_code=row["region_code"],
                year=int(row["year"]),
                prevalent_cases=int(row["prevalent_cases"]),
                population=int(row["population"]),
                prevalence_per_100k=float(row["prevalence_per_100k"]),
            )
            for row in rows
        ]
        return PaginatedResult(items=items, pagination=_build_pagination(filters.page, filters.page_size, total_items))

    def list_mortality(self, filters: RegionTimeFilters) -> PaginatedResult:
        where_clause, query_params = _build_region_time_where(filters, "metric_year", "region_code")
        count_rows = self.client.query_json(
            f"SELECT count(*) AS total_items FROM mortality_facts {where_clause}",
            query_params,
        )
        total_items = int(count_rows[0]["total_items"]) if count_rows else 0
        offset = (filters.page - 1) * filters.page_size
        rows = self.client.query_json(
            f"""
            SELECT
                disease_id,
                disease_name,
                region_code,
                metric_year AS year,
                deaths,
                population,
                mortality_per_100k
            FROM mortality_facts
            {where_clause}
            ORDER BY year DESC, disease_name DESC, region_code DESC
            LIMIT {{limit:UInt64}} OFFSET {{offset:UInt64}}
            """,
            {**query_params, "limit": filters.page_size, "offset": offset},
        )
        items = [
            MortalityAggregate(
                disease_id=row["disease_id"],
                disease_name=row["disease_name"],
                region_code=row["region_code"],
                year=int(row["year"]),
                deaths=int(row["deaths"]),
                population=int(row["population"]),
                mortality_per_100k=float(row["mortality_per_100k"]),
            )
            for row in rows
        ]
        return PaginatedResult(items=items, pagination=_build_pagination(filters.page, filters.page_size, total_items))

    def list_ranked_indication_profiles(self, filters: RankedIndicationsFilters) -> PaginatedResult:
        where_parts: list[str] = []
        query_params: dict[str, object] = {}
        if filters.region is not None:
            where_parts.append("region_code = {region:String}")
            query_params["region"] = filters.region
        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

        count_rows = self.client.query_json(
            f"SELECT count(*) AS total_items FROM indication_profile_facts {where_clause}",
            query_params,
        )
        total_items = min(int(count_rows[0]["total_items"]) if count_rows else 0, filters.limit)
        rows = self.client.query_json(
            f"""
            SELECT
                indication_id,
                indication_name,
                region_code,
                incidence,
                prevalence,
                unmet_need,
                market_size,
                competition_penalty,
                equity_score
            FROM indication_profile_facts
            {where_clause}
            ORDER BY indication_name ASC
            LIMIT {{limit:UInt64}}
            """,
            {**query_params, "limit": filters.limit},
        )
        items = [
            IndicationProfile(
                indication_id=row["indication_id"],
                indication_name=row["indication_name"],
                region_code=row["region_code"],
                incidence=float(row["incidence"]),
                prevalence=float(row["prevalence"]),
                unmet_need=float(row["unmet_need"]),
                market_size=float(row["market_size"]),
                competition_penalty=float(row["competition_penalty"]),
                equity_score=float(row["equity_score"]),
            )
            for row in rows
        ]
        page_items, pagination = _paginate(items, filters.page, filters.page_size, total_items_override=total_items)
        return PaginatedResult(items=page_items, pagination=pagination)


class SyntheticAnalyticsRepository:
    def list_diseases(self, params: PaginationParams) -> PaginatedResult:
        grouped: dict[str, DiseaseListItem] = {}
        for item in INCIDENCE_DATA + PREVALENCE_DATA:
            existing = grouped.get(item.disease_id)
            if existing is None:
                grouped[item.disease_id] = DiseaseListItem(
                    disease_id=item.disease_id,
                    disease_name=item.disease_name,
                    regions=[item.region_code],
                    year_min=item.year,
                    year_max=item.year,
                )
                continue
            if item.region_code not in existing.regions:
                existing.regions.append(item.region_code)
                existing.regions.sort()
            existing.year_min = min(existing.year_min, item.year)
            existing.year_max = max(existing.year_max, item.year)
        items = sorted(grouped.values(), key=lambda disease: disease.disease_name)
        page_items, pagination = _paginate(items, params.page, params.page_size)
        return PaginatedResult(items=page_items, pagination=pagination)

    def list_incidence(self, filters: RegionTimeFilters) -> PaginatedResult:
        filtered = list(INCIDENCE_DATA)
        if filters.region is not None:
            filtered = [item for item in filtered if item.region_code == filters.region]
        if filters.year_from is not None:
            filtered = [item for item in filtered if item.year >= filters.year_from]
        if filters.year_to is not None:
            filtered = [item for item in filtered if item.year <= filters.year_to]
        filtered = sorted(filtered, key=lambda item: (item.year, item.disease_name, item.region_code), reverse=True)
        page_items, pagination = _paginate(filtered, filters.page, filters.page_size)
        return PaginatedResult(items=page_items, pagination=pagination)

    def list_prevalence(self, filters: RegionTimeFilters) -> PaginatedResult:
        filtered = list(PREVALENCE_DATA)
        if filters.region is not None:
            filtered = [item for item in filtered if item.region_code == filters.region]
        if filters.year_from is not None:
            filtered = [item for item in filtered if item.year >= filters.year_from]
        if filters.year_to is not None:
            filtered = [item for item in filtered if item.year <= filters.year_to]
        filtered = sorted(filtered, key=lambda item: (item.year, item.disease_name, item.region_code), reverse=True)
        page_items, pagination = _paginate(filtered, filters.page, filters.page_size)
        return PaginatedResult(items=page_items, pagination=pagination)

    def list_mortality(self, filters: RegionTimeFilters) -> PaginatedResult:
        # Development-only aggregate fallback: derive mortality from incidence until mortality_facts is loaded.
        incidence = self.list_incidence(filters)
        items = [
            MortalityAggregate(
                disease_id=item.disease_id,
                disease_name=item.disease_name,
                region_code=item.region_code,
                year=item.year,
                deaths=max(int(item.incident_cases * 0.018), 0),
                population=item.population,
                mortality_per_100k=round(max((item.incident_cases * 0.018 / item.population) * 100000, 0), 4),
            )
            for item in incidence.items
        ]
        return PaginatedResult(items=items, pagination=incidence.pagination)

    def list_ranked_indication_profiles(self, filters: RankedIndicationsFilters) -> PaginatedResult:
        profiles = list(INDICATION_PROFILES)
        if filters.region is not None:
            profiles = [item for item in profiles if item.region_code == filters.region]
        page_items, pagination = _paginate(profiles[: filters.limit], filters.page, filters.page_size)
        return PaginatedResult(items=page_items, pagination=pagination)


def build_analytics_repository() -> AnalyticsRepository:
    settings = get_settings()
    if settings.db_backend == "postgres":
        primary: AnalyticsRepository = PostgresAnalyticsRepository(
            PostgresClient(
                PostgresConfig(
                    dsn=settings.database_url,
                    schema=settings.pg_schema,
                    timeout_seconds=settings.pg_timeout_seconds,
                )
            )
        )
    else:
        primary = ClickHouseAnalyticsRepository(
            ClickHouseClient(
                ClickHouseConfig(
                    base_url=settings.clickhouse_url,
                    database=settings.clickhouse_database,
                    user=settings.clickhouse_user,
                    password=settings.clickhouse_password,
                    timeout_seconds=settings.clickhouse_timeout_seconds,
                )
            )
        )
    if settings.app_env != "development":
        return primary
    try:
        primary.client.query_json("SELECT 1 AS ok")
        _ensure_dev_indication_profiles_seeded(primary)
        return primary
    except ClickHouseUnavailableError:
        if settings.db_fallback_enabled:
            log_event(logger, logging.WARNING, "repository.synthetic_fallback", reason="backend_unavailable")
            return SyntheticAnalyticsRepository()
        raise


def _ensure_dev_indication_profiles_seeded(repository: AnalyticsRepository) -> None:
    count_rows = repository.client.query_json("SELECT count(*) AS total_items FROM indication_profile_facts")
    total_items = int(count_rows[0]["total_items"]) if count_rows else 0
    if total_items > 0:
        return

    for profile in INDICATION_PROFILES:
        repository.client.query_json(
            """
            INSERT INTO indication_profile_facts
            (
                indication_id,
                indication_name,
                region_code,
                incidence,
                prevalence,
                unmet_need,
                market_size,
                competition_penalty,
                equity_score
            )
            VALUES
            (
                {indication_id:String},
                {indication_name:String},
                {region_code:String},
                {incidence:Float64},
                {prevalence:Float64},
                {unmet_need:Float64},
                {market_size:Float64},
                {competition_penalty:Float64},
                {equity_score:Float64}
            )
            """,
            {
                "indication_id": profile.indication_id,
                "indication_name": profile.indication_name,
                "region_code": profile.region_code,
                "incidence": profile.incidence,
                "prevalence": profile.prevalence,
                "unmet_need": profile.unmet_need,
                "market_size": profile.market_size,
                "competition_penalty": profile.competition_penalty,
                "equity_score": profile.equity_score,
            },
        )
    log_event(logger, logging.INFO, "repository.dev_seeded_indication_profiles", rows=len(INDICATION_PROFILES))


def _build_region_time_where(filters: RegionTimeFilters, year_column: str, region_column: str) -> tuple[str, dict[str, object]]:
    where_parts: list[str] = []
    query_params: dict[str, object] = {}
    if filters.region is not None:
        where_parts.append(f"{region_column} = {{region:String}}")
        query_params["region"] = filters.region
    if filters.year_from is not None:
        where_parts.append(f"{year_column} >= {{year_from:UInt16}}")
        query_params["year_from"] = filters.year_from
    if filters.year_to is not None:
        where_parts.append(f"{year_column} <= {{year_to:UInt16}}")
        query_params["year_to"] = filters.year_to
    return (f"WHERE {' AND '.join(where_parts)}" if where_parts else "", query_params)


def _build_pagination(page: int, page_size: int, total_items: int) -> PaginationMeta:
    total_pages = ceil(total_items / page_size) if total_items else 0
    return PaginationMeta(page=page, page_size=page_size, total_items=total_items, total_pages=total_pages)


def _paginate(items: list, page: int, page_size: int, total_items_override: int | None = None) -> tuple[list, PaginationMeta]:
    total_items = total_items_override if total_items_override is not None else len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end], _build_pagination(page, page_size, total_items)
