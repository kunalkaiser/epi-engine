from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.rows import dict_row

# Reuse the existing unavailable-error so the FastAPI 503 handler (which catches
# ClickHouseUnavailableError) keeps working unchanged regardless of backend.
from apps.api.db import ClickHouseUnavailableError

# ClickHouse server-side parameters look like {name:Type}; psycopg uses %(name)s.
# The repository writes queries in the {name:Type} form for both backends; this
# translator rewrites them for psycopg so the repo layer stays dialect-neutral.
_PARAM_RE = re.compile(r"\{(\w+):[A-Za-z0-9_()]+\}")


def _translate(sql: str) -> str:
    return _PARAM_RE.sub(lambda match: f"%({match.group(1)})s", sql)


@dataclass(frozen=True)
class PostgresConfig:
    dsn: str
    schema: str
    timeout_seconds: int


class PostgresClient:
    """Postgres-backed analogue of ClickHouseClient exposing the same
    ``query_json(sql, parameters)`` surface, so AnalyticsRepository code above
    this seam does not care which backend it talks to.

    A short-lived connection per call keeps the client robust across Railway
    idle/sleep cycles (no stale pooled sockets) — acceptable given the EPI read
    path is low-volume and latency-tolerant.
    """

    def __init__(self, config: PostgresConfig) -> None:
        self.config = config

    def query_json(self, sql: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        statement = _translate(sql)
        params = parameters or {}
        try:
            with psycopg.connect(
                self.config.dsn,
                connect_timeout=self.config.timeout_seconds,
                row_factory=dict_row,
                options=f"-c search_path={self.config.schema},public",
            ) as conn:
                # Disable client-side prepared statements: Supabase routes through
                # pgbouncer (transaction mode), where reused prepared statements
                # raise "prepared statement already exists". Safe to disable here —
                # these are simple low-volume reads.
                conn.prepare_threshold = None
                with conn.cursor() as cursor:
                    cursor.execute(statement, params)
                    if cursor.description is None:
                        return []  # INSERT/DDL — no result set
                    return list(cursor.fetchall())
        except psycopg.OperationalError as exc:
            # connection-level failure → treat as backend-unavailable (→ 503)
            raise ClickHouseUnavailableError("postgres connection failed") from exc
