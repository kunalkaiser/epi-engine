# Worker Pipelines

This directory contains reusable worker-side pipelines for aggregate-safe processing.

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
