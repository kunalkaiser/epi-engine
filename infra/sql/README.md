# ClickHouse Schema

This directory contains the initial ClickHouse schema for EPI Engine.

## Files

- `001_init_schema.sql`: creates the `epi_engine` database and the base dimension and fact tables.
- `002_staging_tables.sql`: creates validated staging tables used by the ingestion pipeline.
- `003_dev_seed_indication_profile_facts.sql`: inserts synthetic development-only indication profile rows when the table is empty.

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
```

## Reset and Reapply

If you want a clean local database, drop and recreate the container data, then run the schema again:

```bash
docker compose down -v
docker compose up -d clickhouse
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/001_init_schema.sql
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/002_staging_tables.sql
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/003_dev_seed_indication_profile_facts.sql
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

Do not apply `003_dev_seed_indication_profile_facts.sql` in staging or production-like environments.
