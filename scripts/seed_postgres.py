#!/usr/bin/env python3
"""
EPI Engine — Postgres (Supabase) seed loader
=============================================
Postgres counterpart of seed_production_data.py. Applies the read-path schema
(infra/sql/pg/001_epi_engine_schema.sql) and loads the SAME public aggregate data
(GBD/CDC/WHO) into the epi_engine schema. Idempotent: truncates fact tables first.

Usage:
    DATABASE_URL='postgresql://USER:PW@HOST:5432/postgres?sslmode=require' \
    python scripts/seed_postgres.py [--schema-only] [--dry-run]

Reuses the canonical data lists from seed_production_data.py so the two backends
stay in lockstep.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg

# Reuse the canonical seed data (module-level lists) so PG and ClickHouse match.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from seed_production_data import INCIDENCE_DATA, PREVALENCE_DATA, INDICATION_PROFILES  # noqa: E402

SCHEMA = os.getenv("PG_SCHEMA", "epi_engine")
SCHEMA_FILE = Path(__file__).resolve().parents[1] / "infra" / "sql" / "pg" / "001_epi_engine_schema.sql"


def _incidence_rows() -> list[tuple]:
    return [
        (did, name, region, "all_ages", year, cases, pop, round(cases / pop * 100_000, 2), source)
        for did, name, region, year, cases, pop, source in INCIDENCE_DATA
    ]


def _prevalence_rows() -> list[tuple]:
    return [
        (did, name, region, "all_ages", year, cases, pop, round(cases / pop * 100_000, 2), source)
        for did, name, region, year, cases, pop, source in PREVALENCE_DATA
    ]


def _indication_rows() -> list[tuple]:
    return [
        (iid, iname, region, inc, prev, unmet, market, comp, equity)
        for iid, iname, region, inc, prev, unmet, market, comp, equity in INDICATION_PROFILES
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--schema-only", action="store_true", help="Apply schema, skip data")
    parser.add_argument("--dry-run", action="store_true", help="Print row counts, do not write")
    args = parser.parse_args()

    if not args.database_url:
        print("ERROR: DATABASE_URL not set (or pass --database-url)", file=sys.stderr)
        return 2

    incidence, prevalence, indications = _incidence_rows(), _prevalence_rows(), _indication_rows()
    print("EPI Engine Postgres Seed" + (" (DRY RUN)" if args.dry_run else ""))
    print(f"  schema: {SCHEMA}")
    print(f"  incidence_facts: {len(incidence)} | prevalence_facts: {len(prevalence)} | indication_profile_facts: {len(indications)}")
    if args.dry_run:
        print("Dry run — no writes.")
        return 0

    with psycopg.connect(args.database_url, options=f"-c search_path={SCHEMA},public") as conn:
        with conn.cursor() as cur:
            print(f"Applying schema from {SCHEMA_FILE.name} ...")
            cur.execute(SCHEMA_FILE.read_text())
            if args.schema_only:
                conn.commit()
                print("  ✓ schema applied (data skipped)")
                return 0

            cur.execute("TRUNCATE incidence_facts, prevalence_facts, indication_profile_facts")
            cur.executemany(
                """INSERT INTO incidence_facts
                   (disease_id, disease_name, region_code, population_segment, metric_year,
                    incident_cases, population, incidence_per_100k, source_name)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                incidence,
            )
            cur.executemany(
                """INSERT INTO prevalence_facts
                   (disease_id, disease_name, region_code, population_segment, metric_year,
                    prevalent_cases, population, prevalence_per_100k, source_name)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                prevalence,
            )
            cur.executemany(
                """INSERT INTO indication_profile_facts
                   (indication_id, indication_name, region_code, incidence, prevalence,
                    unmet_need, market_size, competition_penalty, equity_score)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                indications,
            )
        conn.commit()

    print(f"  ✓ {len(incidence)} incidence, {len(prevalence)} prevalence, {len(indications)} indication rows seeded")
    print("✓ Seed complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
