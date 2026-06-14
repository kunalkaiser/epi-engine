from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_api_dockerfile_matches_expected_entrypoint_and_requirements() -> None:
    dockerfile = (REPO_ROOT / "apps/api/Dockerfile").read_text(encoding="utf-8")

    assert "COPY apps/api/requirements.txt ./apps/api/requirements.txt" in dockerfile
    assert "RUN pip install --no-cache-dir -r apps/api/requirements.txt" in dockerfile
    # CMD binds the platform-provided $PORT (Railway) with an 8000 fallback.
    assert 'CMD ["sh", "-c", "uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]' in dockerfile


def test_web_dockerfile_uses_lockfile_and_builds_next_app() -> None:
    dockerfile = (REPO_ROOT / "apps/web/Dockerfile").read_text(encoding="utf-8")

    assert "COPY apps/web/package-lock.json ./package-lock.json" in dockerfile
    assert "RUN npm ci" in dockerfile
    assert "RUN npm run build" in dockerfile
    assert 'CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0", "--port", "3000"]' in dockerfile


def test_compose_wires_api_web_and_clickhouse_defaults() -> None:
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "dockerfile: apps/api/Dockerfile" in compose
    assert "dockerfile: apps/web/Dockerfile" in compose
    assert "dockerfile: apps/worker/Dockerfile" in compose
    assert "AUTH_JWT_SECRET: ${AUTH_JWT_SECRET:-dev-secret}" in compose
    assert "CLICKHOUSE_URL: http://clickhouse:8123" in compose
    assert "CLICKHOUSE_USER: ${CLICKHOUSE_USER:-epi_engine_app}" in compose
    assert "CLICKHOUSE_PASSWORD: ${CLICKHOUSE_PASSWORD:?CLICKHOUSE_PASSWORD must be set}" in compose
    assert "API_BASE_URL: http://api:8000" in compose
    assert "API_AUTH_TOKEN: ${API_AUTH_TOKEN:-" in compose
    assert "NEXT_PUBLIC_API_BASE_URL: http://localhost:8000" in compose
    assert "NEXT_PUBLIC_API_AUTH_TOKEN" not in compose
    assert "image: clickhouse/clickhouse-server" in compose
    assert "worker ready (development)" not in compose
    assert "healthcheck:" in compose
    assert "condition: service_healthy" in compose


def test_worker_dockerfile_installs_worker_requirements() -> None:
    dockerfile = (REPO_ROOT / "apps/worker/Dockerfile").read_text(encoding="utf-8")

    assert "COPY apps/worker/requirements.txt ./apps/worker/requirements.txt" in dockerfile
    assert "RUN pip install --no-cache-dir -r apps/worker/requirements.txt" in dockerfile
    assert 'CMD ["python", "-m", "apps.worker.worker"]' in dockerfile


def test_dev_seed_sql_exists_for_indication_profile_facts() -> None:
    seed_sql = REPO_ROOT / "infra/sql/003_dev_seed_indication_profile_facts.sql"
    content = seed_sql.read_text(encoding="utf-8")

    assert "INSERT INTO indication_profile_facts" in content
    assert "WHERE (SELECT count() FROM indication_profile_facts) = 0" in content


def test_staging_compose_disables_fallback_and_requires_runtime_env() -> None:
    compose = (REPO_ROOT / "docker-compose.staging.yml").read_text(encoding="utf-8")

    assert "DB_FALLBACK_ENABLED: \"false\"" in compose
    assert "AUTH_JWT_SECRET: ${AUTH_JWT_SECRET:?set AUTH_JWT_SECRET}" in compose
    assert "API_BASE_URL: ${API_BASE_URL:?set API_BASE_URL}" in compose
    assert "API_AUTH_TOKEN: ${API_AUTH_TOKEN:?set API_AUTH_TOKEN}" in compose
    assert "NEXT_PUBLIC_API_BASE_URL: ${NEXT_PUBLIC_API_BASE_URL:?set NEXT_PUBLIC_API_BASE_URL}" in compose
    assert "clickhouse_data:/var/lib/clickhouse" in compose


def test_staging_env_example_exists_with_required_keys() -> None:
    env_example = (REPO_ROOT / ".env.staging.example").read_text(encoding="utf-8")

    assert "AUTH_JWT_SECRET=" in env_example
    assert "CLICKHOUSE_USER=" in env_example
    assert "CLICKHOUSE_PASSWORD=" in env_example
    assert "API_BASE_URL=" in env_example
    assert "API_AUTH_TOKEN=" in env_example
    assert "NEXT_PUBLIC_API_BASE_URL=" in env_example
    assert "WORKER_LOOP_INTERVAL_SECONDS=" in env_example
    assert "WORKER_SIMULATION_BATCH_SIZE=" in env_example
    assert "API_METRICS_ENABLED=" in env_example
    assert "TRACE_HEADER_NAME=" in env_example
    assert "WORKER_HEARTBEAT_FILE=" in env_example


def test_production_env_example_exists_with_required_keys() -> None:
    env_example = (REPO_ROOT / ".env.production.example").read_text(encoding="utf-8")

    assert "APP_ENV=production" in env_example
    assert "DB_FALLBACK_ENABLED=false" in env_example
    assert "AUTH_JWT_SECRET=" in env_example
    assert "CLICKHOUSE_URL=" in env_example
    assert "API_BASE_URL=" in env_example
    assert "API_AUTH_TOKEN=" in env_example
    assert "NEXT_PUBLIC_API_BASE_URL=" in env_example
    assert "WORKER_HEARTBEAT_FILE=" in env_example


def test_staging_workflow_applies_enterprise_sql_extension() -> None:
    workflow = (REPO_ROOT / ".github/workflows/staging.yml").read_text(encoding="utf-8")

    assert "infra/sql/004_enterprise_aggregate_extensions.sql" in workflow
    assert "infra/sql/005_phase2_persistence_and_tenant.sql" in workflow
    assert "infra/sql/006_phase3_intelligence_async_simulation.sql" in workflow
    assert "NEXT_PUBLIC_API_AUTH_TOKEN" in workflow


def test_web_env_validation_script_blocks_public_auth_token() -> None:
    script = (REPO_ROOT / "apps/web/scripts/validate-env.mjs").read_text(encoding="utf-8")
    package_json = (REPO_ROOT / "apps/web/package.json").read_text(encoding="utf-8")
    server_backend = (REPO_ROOT / "apps/web/lib/server-backend.ts").read_text(encoding="utf-8")

    assert "NEXT_PUBLIC_API_AUTH_TOKEN" in script
    assert "validate:env" in package_json
    assert "test:node" in package_json
    assert "npm run validate:env && next build" in package_json
    assert "includePublicFallback" in server_backend


def test_ci_workflow_includes_security_and_web_env_gates() -> None:
    workflow = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "NEXT_PUBLIC_API_AUTH_TOKEN" in workflow
    assert "npm run test:node" in workflow
    assert "APP_ENV: staging" in workflow


def test_frontend_enterprise_routes_are_dynamic() -> None:
    route_files = [
        REPO_ROOT / "apps/web/app/page.tsx",
        REPO_ROOT / "apps/web/app/disease-explorer/page.tsx",
        REPO_ROOT / "apps/web/app/indication-prioritizer/page.tsx",
        REPO_ROOT / "apps/web/app/incidence-prevalence/page.tsx",
        REPO_ROOT / "apps/web/app/determinants-analysis/page.tsx",
        REPO_ROOT / "apps/web/app/simulation-lab/page.tsx",
        REPO_ROOT / "apps/web/app/compare-scenarios/page.tsx",
        REPO_ROOT / "apps/web/app/data-quality-center/page.tsx",
        REPO_ROOT / "apps/web/app/ingestion-run-center/page.tsx",
        REPO_ROOT / "apps/web/app/audit-viewer/page.tsx",
        REPO_ROOT / "apps/web/app/methodology-center/page.tsx",
        REPO_ROOT / "apps/web/app/health-diagnostics/page.tsx",
        REPO_ROOT / "apps/web/app/admin-tenant-settings/page.tsx",
    ]

    for file_path in route_files:
        content = file_path.read_text(encoding="utf-8")
        assert 'export const dynamic = "force-dynamic";' in content
        assert "export const revalidate = 0;" in content


def test_frontend_does_not_use_next_public_auth_token() -> None:
    web_root = REPO_ROOT / "apps/web"
    all_sources = list(web_root.rglob("*.ts")) + list(web_root.rglob("*.tsx"))
    joined = "\n".join(path.read_text(encoding="utf-8") for path in all_sources)

    assert "NEXT_PUBLIC_API_AUTH_TOKEN" not in joined
