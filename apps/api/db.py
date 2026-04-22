from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import error, parse, request


class ClickHouseUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class ClickHouseConfig:
    base_url: str
    database: str
    user: str
    password: str
    timeout_seconds: int


class ClickHouseClient:
    def __init__(self, config: ClickHouseConfig) -> None:
        self.config = config

    def query_json(self, sql: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        query_params = {
            "database": self.config.database,
            "default_format": "JSONEachRow",
        }
        if self.config.user:
            query_params["user"] = self.config.user
        if self.config.password:
            query_params["password"] = self.config.password

        typed_params = parameters or {}
        for key, value in typed_params.items():
            query_params[f"param_{key}"] = _serialize_parameter(value)
        endpoint = f"{self.config.base_url.rstrip('/')}/?{parse.urlencode(query_params)}"
        payload = sql.encode("utf-8")

        http_request = request.Request(endpoint, data=payload, method="POST")
        try:
            with request.urlopen(http_request, timeout=self.config.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except (error.URLError, TimeoutError, OSError) as exc:
            raise ClickHouseUnavailableError("clickhouse query failed") from exc

        rows: list[dict[str, Any]] = []
        for line in body.splitlines():
            if not line.strip():
                continue
            rows.append(json.loads(line))
        return rows


def _serialize_parameter(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)
