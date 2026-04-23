from __future__ import annotations

import logging

from apps.api.logging_utils import log_event


def test_log_event_redacts_secret_fields(caplog) -> None:
    logger = logging.getLogger("tests.logging")
    with caplog.at_level(logging.INFO):
        log_event(
            logger,
            logging.INFO,
            "security.test",
            auth_token="abc123",
            clickhouse_password="super-secret",
            authorization="Bearer value",
            safe_field="ok",
        )

    message = caplog.records[-1].message
    assert "auth_token=***REDACTED***" in message
    assert "clickhouse_password=***REDACTED***" in message
    assert "authorization=***REDACTED***" in message
    assert "safe_field=ok" in message
    assert "abc123" not in message
    assert "super-secret" not in message
