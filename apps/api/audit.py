import logging
from dataclasses import asdict, dataclass
from typing import Any

from apps.api.logging_utils import log_event


logger = logging.getLogger("epi_engine.audit")


@dataclass(frozen=True)
class AuditEvent:
    event_name: str
    payload: dict[str, Any]


_AUDIT_EVENTS: list[AuditEvent] = []


def audit_log(event_name: str, payload: dict[str, Any]) -> None:
    # Stub for future structured audit persistence.
    _AUDIT_EVENTS.append(AuditEvent(event_name=event_name, payload=payload))
    log_event(logger, logging.INFO, "audit", event_name=event_name, **payload)


def audit_log_access(
    event_name: str,
    role: str,
    resource: str,
    outcome: str,
    detail: str | None = None,
    subject: str | None = None,
) -> None:
    payload = {
        "role": role,
        "resource": resource,
        "outcome": outcome,
    }
    if subject is not None:
        payload["subject"] = subject
    if detail is not None:
        payload["detail"] = detail
    audit_log(event_name, payload)


def audit_log_export(
    role: str,
    export_type: str,
    outcome: str,
    detail: str,
    subject: str | None = None,
) -> None:
    payload = {
        "role": role,
        "export_type": export_type,
        "outcome": outcome,
        "detail": detail,
    }
    if subject is not None:
        payload["subject"] = subject
    audit_log("export.attempt", payload)


def get_audit_events() -> list[dict[str, Any]]:
    return [asdict(event) for event in _AUDIT_EVENTS]


def clear_audit_events() -> None:
    _AUDIT_EVENTS.clear()
