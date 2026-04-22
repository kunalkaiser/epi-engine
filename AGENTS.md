# EPI Engine Rules

You are building a healthcare epidemiology decision-support platform.

DO:
- Write clean, modular, typed code
- Use FastAPI (backend) and Next.js (frontend)
- Use ClickHouse for analytics
- Add tests for core logic
- Keep files small and readable

DO NOT:
- Build patient-level clinical decision tools
- Assume HIPAA compliance is complete
- Hardcode credentials or secrets
- Expose PHI in logs or examples

ARCHITECTURE:
- apps/api -> FastAPI
- apps/web -> Next.js
- apps/worker -> background jobs
- packages/shared-types -> schemas
- infra/sql -> database schema

OUTPUT STYLE:
- Always explain what files you modify
- Keep implementations minimal and correct
- Prefer clarity over complexity
