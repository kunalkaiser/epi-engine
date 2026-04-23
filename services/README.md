# EpiOS Service Boundaries

This folder defines top-level service boundaries used by EpiOS.

Current implementation uses `apps/api` and `apps/worker` runtime processes, while these
modules provide stable service contracts and ownership boundaries for future extraction
to independently deployable services when needed.

Services:

- `ingestion-service`
- `analytics-service`
- `determinants-service`
- `prioritization-service`
- `simulation-service`
- `audit-service`
