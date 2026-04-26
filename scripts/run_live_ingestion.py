"""
EPI Engine — Live Ingestion CLI
================================
Pulls from OpenFDA, ClinicalTrials.gov, and OpenTargets.
Writes results to ClickHouse epi_engine database.

Usage:
    # Dry run — fetch from APIs and show row counts, write nothing:
    python scripts/run_live_ingestion.py --dry-run

    # Live run with env vars:
    CLICKHOUSE_URL=https://host:8443 \
    CLICKHOUSE_USER=epi_engine_app \
    CLICKHOUSE_PASSWORD=... \
    python scripts/run_live_ingestion.py

    # Override URL inline:
    python scripts/run_live_ingestion.py \
        --clickhouse-url https://host:8443 \
        --user epi_engine_app \
        --password "..."
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apps.worker.live_ingestion import LIVE_ADAPTERS, run_live_ingestion


def main() -> None:
    parser = argparse.ArgumentParser(
        description="EPI Engine live ingestion — OpenFDA, ClinicalTrials.gov, OpenTargets"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch from APIs and print row counts without writing to ClickHouse",
    )
    parser.add_argument("--clickhouse-url", default=None, help="Override CLICKHOUSE_URL")
    parser.add_argument("--user", default=None, help="Override CLICKHOUSE_USER")
    parser.add_argument("--password", default=None, help="Override CLICKHOUSE_PASSWORD")
    args = parser.parse_args()

    mode = "DRY RUN" if args.dry_run else "LIVE"
    print(f"\nEPI Engine Live Ingestion — {mode}")
    print(f"Sources: {', '.join(a.source_kind for a in LIVE_ADAPTERS)}\n")

    results = run_live_ingestion(
        dry_run=args.dry_run,
        clickhouse_url=args.clickhouse_url,
        clickhouse_user=args.user,
        clickhouse_password=args.password,
    )

    any_error = False
    for r in results:
        status = r["status"]
        icon = "✓" if status in ("ok", "dry_run") else "✗"
        rows = r["rows_fetched"]
        table = r.get("table", "—")
        source = r["source"]

        if status == "error":
            any_error = True
            print(f"  {icon} {source}")
            print(f"      ERROR: {r.get('error', 'unknown')}")
        else:
            prov = r.get("provenance", {})
            prov_str = "  ".join(f"{k}={v}" for k, v in prov.items())
            write_info = f"→ {table}" if status == "ok" else "(not written)"
            print(f"  {icon} {source}")
            print(f"      rows: {rows}  {write_info}")
            if prov_str:
                print(f"      {prov_str}")

    print()
    if args.dry_run:
        print("Dry run complete — no data written to ClickHouse.")
    elif any_error:
        print("Ingestion complete with errors. Check logs.")
        sys.exit(1)
    else:
        print("Ingestion complete.")
        print("\nTables written:")
        for r in results:
            if r["status"] == "ok":
                print(f"  epi_engine.{r['table']}  ({r['rows_fetched']} rows)")


if __name__ == "__main__":
    main()
