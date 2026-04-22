from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path("/Users/kunal/epi-engine")


def test_api_dockerfile_matches_expected_entrypoint_and_requirements() -> None:
    dockerfile = (REPO_ROOT / "apps/api/Dockerfile").read_text(encoding="utf-8")

    assert "COPY apps/api/requirements.txt ./apps/api/requirements.txt" in dockerfile
    assert "RUN pip install --no-cache-dir -r apps/api/requirements.txt" in dockerfile
    assert 'CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]' in dockerfile


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
    assert "CLICKHOUSE_PASSWORD: ${CLICKHOUSE_PASSWORD:-epi_engine_dev_password}" in compose
    assert "NEXT_PUBLIC_API_BASE_URL: http://localhost:8000" in compose
    assert "image: clickhouse/clickhouse-server" in compose


def test_worker_dockerfile_installs_worker_requirements() -> None:
    dockerfile = (REPO_ROOT / "apps/worker/Dockerfile").read_text(encoding="utf-8")

    assert "COPY apps/worker/requirements.txt ./apps/worker/requirements.txt" in dockerfile
    assert "RUN pip install --no-cache-dir -r apps/worker/requirements.txt" in dockerfile


def test_dev_seed_sql_exists_for_indication_profile_facts() -> None:
    seed_sql = REPO_ROOT / "infra/sql/003_dev_seed_indication_profile_facts.sql"
    content = seed_sql.read_text(encoding="utf-8")

    assert "INSERT INTO indication_profile_facts" in content
    assert "WHERE (SELECT count() FROM indication_profile_facts) = 0" in content


def test_staging_compose_disables_fallback_and_requires_runtime_env() -> None:
    compose = (REPO_ROOT / "docker-compose.staging.yml").read_text(encoding="utf-8")

    assert "DB_FALLBACK_ENABLED: \"false\"" in compose
    assert "AUTH_JWT_SECRET: ${AUTH_JWT_SECRET:?set AUTH_JWT_SECRET}" in compose
    assert "NEXT_PUBLIC_API_BASE_URL: ${NEXT_PUBLIC_API_BASE_URL:?set NEXT_PUBLIC_API_BASE_URL}" in compose
    assert "clickhouse_data:/var/lib/clickhouse" in compose


def test_staging_env_example_exists_with_required_keys() -> None:
    env_example = (REPO_ROOT / ".env.staging.example").read_text(encoding="utf-8")

    assert "AUTH_JWT_SECRET=" in env_example
    assert "CLICKHOUSE_USER=" in env_example
    assert "CLICKHOUSE_PASSWORD=" in env_example
    assert "NEXT_PUBLIC_API_BASE_URL=" in env_example
