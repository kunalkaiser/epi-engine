from __future__ import annotations

import logging
from typing import Any


REDACTED_KEYS = ("password", "secret", "token", "authorization", "api_key", "credential")


def configure_logging(log_level: str) -> None:
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=getattr(logging, log_level.upper(), logging.INFO),
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
    else:
        root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger: logging.Logger, level: int, message: str, **fields: Any) -> None:
    if fields:
        safe_fields = {key: _sanitize_value(key, value) for key, value in sorted(fields.items())}
        details = " ".join(f"{key}={value}" for key, value in safe_fields.items())
        logger.log(level, "%s %s", message, details)
        return
    logger.log(level, message)


def _sanitize_value(key: str, value: Any) -> Any:
    key_lower = key.lower()
    if any(pattern in key_lower for pattern in REDACTED_KEYS):
        return "***REDACTED***"
    if isinstance(value, dict):
        return {k: _sanitize_value(k, v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(key, item) for item in value]
    if isinstance(value, str) and "bearer " in value.lower():
        return "***REDACTED***"
    return value
