# ClickHouse Schema

This directory contains the initial ClickHouse schema for EPI Engine.

## Files

- `001_init_schema.sql`: creates the `epi_engine` database and the base dimension and fact tables.
- `002_staging_tables.sql`: creates validated staging tables used by the ingestion pipeline.
- `003_dev_seed_indication_profile_facts.sql`: inserts synthetic development-only indication profile rows when the table is empty.
- `004_enterprise_aggregate_extensions.sql`: adds aggregate enterprise extensions (mortality, determinants summaries, simulation snapshots, ingestion runs, and data quality results).
- `005_phase2_persistence_and_tenant.sql`: adds durable tenant-scoped simulation, ingestion, and data-quality persistence tables.
- `006_phase3_intelligence_async_simulation.sql`: extends simulation persistence for async jobs, retries, uncertainty bands, and run event traceability.

## Run Locally

Start ClickHouse with Docker Compose from the repo root:

```bash
docker compose up -d clickhouse
```

Apply the schema:

```bash
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/001_init_schema.sql
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/002_staging_tables.sql
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/003_dev_seed_indication_profile_facts.sql
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/004_enterprise_aggregate_extensions.sql
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/005_phase2_persistence_and_tenant.sql
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/006_phase3_intelligence_async_simulation.sql
```

## Reset and Reapply

If you want a clean local database, drop and recreate the container data, then run the schema again:

```bash
docker compose down -v
docker compose up -d clickhouse
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/001_init_schema.sql
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/002_staging_tables.sql
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/003_dev_seed_indication_profile_facts.sql
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/004_enterprise_aggregate_extensions.sql
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/005_phase2_persistence_and_tenant.sql
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/006_phase3_intelligence_async_simulation.sql
```

## Notes

- Fact tables are partitioned by time to support trend queries and bulk reloads.
- Sort keys favor region, disease, and date filters used by the V1 explorer and prioritization flows.
- `dim_patient` is de-identified and intended only for aggregate cohort analysis.
- The dev seed file is synthetic and should not be used for non-development environments.

## Staging Apply Order

For staging environments, apply only:

1. `001_init_schema.sql`
2. `002_staging_tables.sql`
3. `004_enterprise_aggregate_extensions.sql`
4. `005_phase2_persistence_and_tenant.sql`
5. `006_phase3_intelligence_async_simulation.sql`

Do not apply `003_dev_seed_indication_profile_facts.sql` in staging or production-like environments.
