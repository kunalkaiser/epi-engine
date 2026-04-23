from __future__ import annotations

from apps.api.platform_models import AuditEventsResponse
from apps.api.platform_services import get_audit_events_page


def list_audit_events(page: int, page_size: int) -> AuditEventsResponse:
    items, pagination = get_audit_events_page(page, page_size)
    return AuditEventsResponse(items=items, pagination=pagination)
