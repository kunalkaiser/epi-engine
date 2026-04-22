from __future__ import annotations

from urllib import error

import pytest

from apps.api.db import ClickHouseClient, ClickHouseConfig, ClickHouseUnavailableError, _serialize_parameter


class _FakeResponse:
    def __init__(self, body: str) -> None:
        self._body = body.encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def _config() -> ClickHouseConfig:
    return ClickHouseConfig(
        base_url="http://clickhouse:8123",
        database="epi_engine",
        user="default",
        password="secret",
        timeout_seconds=3,
    )


def test_clickhouse_client_sends_typed_parameters(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["data"] = req.data.decode("utf-8")
        captured["timeout"] = timeout
        return _FakeResponse('{"ok":1}\n{"ok":2}\n')

    monkeypatch.setattr("apps.api.db.request.urlopen", fake_urlopen)
    client = ClickHouseClient(_config())

    rows = client.query_json(
        "SELECT * FROM table WHERE region = {region:String} AND year = {year:UInt16}",
        {"region": "US", "year": 2025, "enabled": True},
    )

    assert rows == [{"ok": 1}, {"ok": 2}]
    assert "database=epi_engine" in str(captured["url"])
    assert "default_format=JSONEachRow" in str(captured["url"])
    assert "param_region=US" in str(captured["url"])
    assert "param_year=2025" in str(captured["url"])
    assert "param_enabled=1" in str(captured["url"])
    assert captured["data"] == "SELECT * FROM table WHERE region = {region:String} AND year = {year:UInt16}"
    assert captured["timeout"] == 3


def test_clickhouse_client_raises_unavailable_on_url_error(monkeypatch) -> None:
    def fake_urlopen(_req, timeout=None):
        raise error.URLError("down")

    monkeypatch.setattr("apps.api.db.request.urlopen", fake_urlopen)
    client = ClickHouseClient(_config())

    with pytest.raises(ClickHouseUnavailableError):
        client.query_json("SELECT 1")


def test_serialize_parameter_handles_basic_types() -> None:
    assert _serialize_parameter(None) == ""
    assert _serialize_parameter(True) == "1"
    assert _serialize_parameter(False) == "0"
    assert _serialize_parameter(12) == "12"
    assert _serialize_parameter("us") == "us"
