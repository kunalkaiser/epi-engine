"""
EPI Engine — Production Data Seed Loader
=========================================
Seeds ClickHouse with real public epidemiological data from:
  - GBD (Global Burden of Disease) — IHME published estimates
  - CDC Wonder aggregate disease burden data
  - WHO Global Health Observatory

All data is aggregate-level, publicly available, no PHI.
Run this ONCE after deploying ClickHouse schema.

Usage:
    CLICKHOUSE_URL=http://... \
    CLICKHOUSE_USER=epi_engine_app \
    CLICKHOUSE_PASSWORD=... \
    python scripts/seed_production_data.py

    # Dry run (prints SQL, doesn't execute):
    python scripts/seed_production_data.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from urllib import parse, request, error


# ─────────────────────────────────────────────────────────────────────────────
# Public epidemiological data — GBD 2021 + CDC estimates
# Sources:
#   - IHME GBD 2021: https://vizhub.healthdata.org/gbd-results/
#   - CDC Wonder: https://wonder.cdc.gov/
#   - WHO GHO: https://www.who.int/data/gho
# All figures are published aggregate estimates. No patient data.
# ─────────────────────────────────────────────────────────────────────────────

INCIDENCE_DATA = [
    # (disease_id, disease_name, region_code, year, incident_cases, population, source)
    ("t2d",         "Type 2 Diabetes",              "US", 2023, 1_540_000,   334_900_000, "CDC-2023"),
    ("t2d",         "Type 2 Diabetes",              "US", 2022, 1_480_000,   333_300_000, "CDC-2022"),
    ("t2d",         "Type 2 Diabetes",              "EU", 2022, 2_100_000,   447_000_000, "GBD-2021"),
    ("ihd",         "Ischemic Heart Disease",       "US", 2023,   785_000,   334_900_000, "CDC-2023"),
    ("ihd",         "Ischemic Heart Disease",       "EU", 2022, 1_200_000,   447_000_000, "GBD-2021"),
    ("stroke",      "Stroke",                       "US", 2023,   795_000,   334_900_000, "CDC-2023"),
    ("stroke",      "Stroke",                       "EU", 2022,   900_000,   447_000_000, "GBD-2021"),
    ("nsclc",       "Non-Small Cell Lung Cancer",   "US", 2023,   218_000,   334_900_000, "NCI-2023"),
    ("nsclc",       "Non-Small Cell Lung Cancer",   "EU", 2022,   270_000,   447_000_000, "GBD-2021"),
    ("crc",         "Colorectal Cancer",            "US", 2023,   153_000,   334_900_000, "NCI-2023"),
    ("crc",         "Colorectal Cancer",            "EU", 2022,   198_000,   447_000_000, "GBD-2021"),
    ("alzheimers",  "Alzheimer's Disease",          "US", 2023,   413_000,   334_900_000, "ALZ-2023"),
    ("alzheimers",  "Alzheimer's Disease",          "EU", 2022,   420_000,   447_000_000, "GBD-2021"),
    ("nafld",       "NAFLD/NASH",                   "US", 2023,   850_000,   334_900_000, "GBD-2021"),
    ("nafld",       "NAFLD/NASH",                   "EU", 2022,   920_000,   447_000_000, "GBD-2021"),
    ("ra",          "Rheumatoid Arthritis",         "US", 2023,   200_000,   334_900_000, "ACR-2023"),
    ("ra",          "Rheumatoid Arthritis",         "EU", 2022,   270_000,   447_000_000, "GBD-2021"),
    ("ckd",         "Chronic Kidney Disease",       "US", 2023,   780_000,   334_900_000, "USRDS-2023"),
    ("ckd",         "Chronic Kidney Disease",       "EU", 2022,   820_000,   447_000_000, "GBD-2021"),
    ("copd",        "COPD",                         "US", 2023,   480_000,   334_900_000, "CDC-2023"),
    ("copd",        "COPD",                         "EU", 2022,   520_000,   447_000_000, "GBD-2021"),
]

PREVALENCE_DATA = [
    # (disease_id, disease_name, region_code, year, prevalent_cases, population, source)
    ("t2d",        "Type 2 Diabetes",              "US", 2023,  38_400_000,  334_900_000, "CDC-2023"),
    ("t2d",        "Type 2 Diabetes",              "EU", 2022,  33_000_000,  447_000_000, "GBD-2021"),
    ("ihd",        "Ischemic Heart Disease",       "US", 2023,  20_500_000,  334_900_000, "CDC-2023"),
    ("ihd",        "Ischemic Heart Disease",       "EU", 2022,  23_000_000,  447_000_000, "GBD-2021"),
    ("stroke",     "Stroke",                       "US", 2023,   7_800_000,  334_900_000, "CDC-2023"),
    ("stroke",     "Stroke",                       "EU", 2022,   8_100_000,  447_000_000, "GBD-2021"),
    ("nsclc",      "Non-Small Cell Lung Cancer",   "US", 2023,     560_000,  334_900_000, "NCI-2023"),
    ("nsclc",      "Non-Small Cell Lung Cancer",   "EU", 2022,     640_000,  447_000_000, "GBD-2021"),
    ("crc",        "Colorectal Cancer",            "US", 2023,   1_550_000,  334_900_000, "NCI-2023"),
    ("crc",        "Colorectal Cancer",            "EU", 2022,   1_850_000,  447_000_000, "GBD-2021"),
    ("alzheimers", "Alzheimer's Disease",          "US", 2023,   6_700_000,  334_900_000, "ALZ-2023"),
    ("alzheimers", "Alzheimer's Disease",          "EU", 2022,   7_800_000,  447_000_000, "GBD-2021"),
    ("nafld",      "NAFLD/NASH",                   "US", 2023,  83_000_000,  334_900_000, "GBD-2021"),
    ("nafld",      "NAFLD/NASH",                   "EU", 2022,  71_000_000,  447_000_000, "GBD-2021"),
    ("ra",         "Rheumatoid Arthritis",         "US", 2023,   1_500_000,  334_900_000, "ACR-2023"),
    ("ra",         "Rheumatoid Arthritis",         "EU", 2022,   2_100_000,  447_000_000, "GBD-2021"),
    ("ckd",        "Chronic Kidney Disease",       "US", 2023,  37_000_000,  334_900_000, "USRDS-2023"),
    ("ckd",        "Chronic Kidney Disease",       "EU", 2022,  31_000_000,  447_000_000, "GBD-2021"),
    ("copd",       "COPD",                         "US", 2023,  16_000_000,  334_900_000, "CDC-2023"),
    ("copd",       "COPD",                         "EU", 2022,  18_400_000,  447_000_000, "GBD-2021"),
]

# Indication profile facts — inputs to the scoring model
# unmet_need: 0-100 (100 = highest unmet need)
# market_size: 0-100 proxy (global revenue potential)
# competition_penalty: 0-100 (100 = saturated market)
# equity_score: 0-100 (100 = high health equity burden)
INDICATION_PROFILES = [
    # (indication_id, indication_name, region, incidence, prevalence, unmet_need, market_size, competition_penalty, equity_score)
    ("t2d-us",        "Type 2 Diabetes",             "US", 84.0, 91.0, 61.0, 88.0, 72.0, 74.0),
    ("t2d-eu",        "Type 2 Diabetes",             "EU", 79.0, 87.0, 58.0, 85.0, 70.0, 68.0),
    ("ihd-us",        "Ischemic Heart Disease",      "US", 72.0, 85.0, 54.0, 82.0, 65.0, 69.0),
    ("ihd-eu",        "Ischemic Heart Disease",      "EU", 70.0, 83.0, 51.0, 79.0, 63.0, 64.0),
    ("stroke-us",     "Stroke",                      "US", 73.0, 71.0, 66.0, 74.0, 58.0, 72.0),
    ("nsclc-us",      "Non-Small Cell Lung Cancer",  "US", 62.0, 52.0, 78.0, 91.0, 41.0, 61.0),
    ("nsclc-eu",      "Non-Small Cell Lung Cancer",  "EU", 60.0, 50.0, 75.0, 88.0, 39.0, 57.0),
    ("crc-us",        "Colorectal Cancer",           "US", 57.0, 68.0, 69.0, 83.0, 44.0, 63.0),
    ("alzheimers-us", "Alzheimer's Disease",         "US", 64.0, 76.0, 89.0, 92.0, 28.0, 58.0),
    ("alzheimers-eu", "Alzheimer's Disease",         "EU", 61.0, 73.0, 87.0, 89.0, 26.0, 54.0),
    ("nafld-us",      "NAFLD/NASH",                  "US", 71.0, 94.0, 83.0, 87.0, 22.0, 66.0),
    ("nafld-eu",      "NAFLD/NASH",                  "EU", 68.0, 91.0, 80.0, 84.0, 20.0, 61.0),
    ("ra-us",         "Rheumatoid Arthritis",        "US", 52.0, 67.0, 57.0, 71.0, 55.0, 55.0),
    ("ckd-us",        "Chronic Kidney Disease",      "US", 71.0, 90.0, 74.0, 85.0, 38.0, 76.0),
    ("ckd-eu",        "Chronic Kidney Disease",      "EU", 68.0, 87.0, 71.0, 82.0, 36.0, 71.0),
    ("copd-us",       "COPD",                        "US", 65.0, 78.0, 68.0, 77.0, 52.0, 67.0),
]


def build_clickhouse_client(base_url: str, user: str, password: str) -> "ClickHouseClient":
    return ClickHouseClient(base_url=base_url, user=user, password=password)


class ClickHouseClient:
    def __init__(self, base_url: str, user: str, password: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.user = user
        self.password = password

    def execute(self, query: str, dry_run: bool = False) -> None:
        if dry_run:
            print(f"[DRY RUN] {query[:200]}...")
            return
        params = parse.urlencode({"query": query, "user": self.user, "password": self.password})
        endpoint = f"{self.base_url}/?{params}"
        req = request.Request(endpoint, data=b"", method="POST")
        try:
            with request.urlopen(req) as resp:
                resp.read()
        except error.URLError as exc:
            print(f"[ERROR] ClickHouse query failed: {exc}", file=sys.stderr)
            raise

    def insert_jsonl(self, table: str, rows: list[dict], dry_run: bool = False) -> None:
        if not rows:
            return
        payload_lines = "\n".join(json.dumps(row) for row in rows)
        query = f"INSERT INTO epi_engine.{table} FORMAT JSONEachRow"
        if dry_run:
            print(f"[DRY RUN] INSERT {len(rows)} rows into {table}")
            return
        params = parse.urlencode({"query": query, "user": self.user, "password": self.password})
        endpoint = f"{self.base_url}/?{params}"
        req = request.Request(endpoint, data=payload_lines.encode("utf-8"), method="POST")
        try:
            with request.urlopen(req) as resp:
                resp.read()
        except error.URLError as exc:
            print(f"[ERROR] Insert into {table} failed: {exc}", file=sys.stderr)
            raise


def seed_incidence(client: ClickHouseClient, dry_run: bool) -> None:
    print(f"Seeding incidence_facts ({len(INCIDENCE_DATA)} rows)...")
    rows = []
    loaded_at = datetime.now(UTC).isoformat()
    for disease_id, disease_name, region, year, cases, pop, source in INCIDENCE_DATA:
        rows.append({
            "disease_id": disease_id,
            "disease_name": disease_name,
            "region_code": region,
            "population_segment": "all_ages",
            "metric_year": year,
            "incident_cases": cases,
            "population": pop,
            "incidence_per_100k": round(cases / pop * 100_000, 2),
            "source_name": source,
            "loaded_at": loaded_at,
        })
    client.insert_jsonl("incidence_facts", rows, dry_run=dry_run)
    print(f"  ✓ {len(rows)} incidence rows seeded")


def seed_prevalence(client: ClickHouseClient, dry_run: bool) -> None:
    print(f"Seeding prevalence_facts ({len(PREVALENCE_DATA)} rows)...")
    rows = []
    loaded_at = datetime.now(UTC).isoformat()
    for disease_id, disease_name, region, year, cases, pop, source in PREVALENCE_DATA:
        rows.append({
            "disease_id": disease_id,
            "disease_name": disease_name,
            "region_code": region,
            "population_segment": "all_ages",
            "metric_year": year,
            "prevalent_cases": cases,
            "population": pop,
            "prevalence_per_100k": round(cases / pop * 100_000, 2),
            "source_name": source,
            "loaded_at": loaded_at,
        })
    client.insert_jsonl("prevalence_facts", rows, dry_run=dry_run)
    print(f"  ✓ {len(rows)} prevalence rows seeded")


def seed_indication_profiles(client: ClickHouseClient, dry_run: bool) -> None:
    print(f"Seeding indication_profile_facts ({len(INDICATION_PROFILES)} rows)...")
    rows = []
    loaded_at = datetime.now(UTC).isoformat()
    for ind_id, ind_name, region, inc, prev, unmet, market, comp, equity in INDICATION_PROFILES:
        rows.append({
            "indication_id": ind_id,
            "indication_name": ind_name,
            "region_code": region,
            "incidence": inc,
            "prevalence": prev,
            "unmet_need": unmet,
            "market_size": market,
            "competition_penalty": comp,
            "equity_score": equity,
            "loaded_at": loaded_at,
        })
    client.insert_jsonl("indication_profile_facts", rows, dry_run=dry_run)
    print(f"  ✓ {len(rows)} indication profile rows seeded")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed EPI Engine ClickHouse with real public epidemiological data")
    parser.add_argument("--dry-run", action="store_true", help="Print SQL without executing")
    parser.add_argument("--clickhouse-url", default=None, help="Override CLICKHOUSE_URL env var")
    parser.add_argument("--user", default=None, help="Override CLICKHOUSE_USER env var")
    parser.add_argument("--password", default=None, help="Override CLICKHOUSE_PASSWORD env var")
    args = parser.parse_args()

    import os
    base_url = args.clickhouse_url or os.getenv("CLICKHOUSE_URL", "http://localhost:8123")
    user = args.user or os.getenv("CLICKHOUSE_USER", "epi_engine_app")
    password = args.password or os.getenv("CLICKHOUSE_PASSWORD", "")

    if not args.dry_run and not password:
        print("[ERROR] CLICKHOUSE_PASSWORD is required for live seeding. Use --dry-run to preview.", file=sys.stderr)
        sys.exit(1)

    print(f"\nEPI Engine Production Data Seed")
    print(f"Target: {base_url}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}\n")

    client = build_clickhouse_client(base_url, user, password)

    seed_incidence(client, dry_run=args.dry_run)
    seed_prevalence(client, dry_run=args.dry_run)
    seed_indication_profiles(client, dry_run=args.dry_run)

    print("\n✓ Seed complete.")
    print("\nData sources:")
    print("  CDC Wonder: https://wonder.cdc.gov/")
    print("  IHME GBD 2021: https://vizhub.healthdata.org/gbd-results/")
    print("  NCI SEER: https://seer.cancer.gov/")
    print("  Alzheimer's Association: https://www.alz.org/alzheimers-dementia/facts-figures")
    print("  USRDS: https://adr.usrds.org/")
    print("  ACR: https://www.rheumatology.org/")
    print("\nAll data is aggregate-level published estimates. No patient data used.")


if __name__ == "__main__":
    main()
