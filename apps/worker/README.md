# Worker Pipelines

This directory contains reusable worker-side pipelines for aggregate-safe processing.

## Runtime Worker Loop

The container/runtime entrypoint is `python -m apps.worker.worker`. It executes a periodic scheduling tick for ingestion refresh, score recompute, and data-quality checks.
It also processes queued simulation runs asynchronously.

Environment variables:

- `WORKER_LOOP_INTERVAL_SECONDS` (default `60`)
- `WORKER_RUN_ONCE` (default `false`, useful for smoke tests)
- `WORKER_SIMULATION_BATCH_SIZE` (default `5`)

## Ingestion Source Kinds and Environment Policy

Runtime ingestion contract:

- `apps.worker.ingestion.ingest_file(...)` accepts only registered source kinds.
- Allowed kinds are defined by `apps.worker.source_adapters.supported_source_kinds()`.
- Unsupported values fail with a deterministic error:
  - `unsupported source_kind: <value>`

Policy contract by environment:

- Development/test may use `synthetic` fixtures for local iteration.
- Staging/production should use enterprise adapter kinds (`ehr_aggregate`, `claims_aggregate`, `registry_aggregate`, `genomic_summary`, `benchmark_reference`, `literature_metadata`) with operator-managed connectors.
- Adapter boundaries are real and stable in code; external connector credentials and transport remain operator-managed outside repo code.

## Clustering

The clustering pipeline accepts only `synthetic` or `deidentified` inputs and produces cluster summaries plus evaluation metrics.

### Supported algorithms

- `kmeans`
- `dbscan`

### What the pipeline outputs

- cluster-level summaries only
- evaluation metrics such as silhouette score, Davies-Bouldin score, and KMeans inertia
- no patient-level decisions or export recommendations

### Run with CSV input

```bash
python3 -m apps.worker.clustering \
  --input-path data/synthetic_cohorts.csv \
  --output-path /tmp/cluster-report.json \
  --source-kind synthetic \
  --feature-columns incidence_rate,prevalence_rate,unmet_need_index,market_size_index,equity_index \
  --algorithm kmeans \
  --n-clusters 3 \
  --random-seed 42
```

### Run with DBSCAN

```bash
python3 -m apps.worker.clustering \
  --input-path data/synthetic_cohorts.csv \
  --output-path /tmp/cluster-report.json \
  --source-kind deidentified \
  --feature-columns incidence_rate,prevalence_rate,unmet_need_index,market_size_index,equity_index \
  --algorithm dbscan \
  --eps 1.2 \
  --min-samples 2
```

### Notes

- Inputs must not contain obvious direct identifiers such as names, addresses, phone numbers, email, SSN, or MRN columns.
- Feature columns must be numeric.
- The JSON report contains aggregate cluster summaries only, including cluster sizes and feature ranges.
