from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Callable, Literal

from fastapi import Header, HTTPException, status
from pydantic import BaseModel, TypeAdapter, ValidationError

from apps.api.audit import audit_log_access
from apps.api.settings import get_settings


Role = Literal["admin", "analyst", "payer_aggregate_only", "trial_coordinator", "read_only_gov"]
_ROLE_ADAPTER = TypeAdapter(Role)


class AuthClaims(BaseModel):
    sub: str
    role: str
    iss: str | None = None
    aud: str | None = None
    exp: int | None = None


def require_role(resource: str, allowed_roles: set[Role]) -> Callable[[str | None], Role]:
    def dependency(authorization: str | None = Header(default=None, alias="Authorization")) -> Role:
        claims = _authenticate_claims(resource=resource, authorization=authorization)
        if claims.role not in allowed_roles:
            detail = f"role {claims.role} is not allowed to access {resource}"
            audit_log_access(
                "access.denied",
                role=claims.role,
                resource=resource,
                outcome="denied",
                detail=detail,
                subject=claims.sub,
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

        audit_log_access(
            "access.allowed",
            role=claims.role,
            resource=resource,
            outcome="allowed",
            subject=claims.sub,
        )
        return claims.role

    return dependency


def require_authenticated_claims(resource: str) -> Callable[[str | None], AuthClaims]:
    def dependency(authorization: str | None = Header(default=None, alias="Authorization")) -> AuthClaims:
        claims = _authenticate_claims(resource=resource, authorization=authorization)
        audit_log_access(
            "access.allowed",
            role=claims.role,
            resource=resource,
            outcome="allowed",
            subject=claims.sub,
        )
        return claims

    return dependency


def _authenticate_claims(resource: str, authorization: str | None) -> AuthClaims:
    if authorization is None:
        return _raise_unauthorized(resource, "missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return _raise_unauthorized(resource, "invalid Authorization header")

    try:
        payload = decode_bearer_token(token)
        claims = AuthClaims.model_validate(payload)
    except (ValueError, ValidationError) as exc:
        return _raise_unauthorized(resource, str(exc))

    try:
        role = _ROLE_ADAPTER.validate_python(claims.role)
    except ValidationError:
        return _raise_unauthorized(resource, f"role {claims.role} is not recognized")

    return AuthClaims(
        sub=claims.sub,
        role=role,
        iss=claims.iss,
        aud=claims.aud,
        exp=claims.exp,
    )


def decode_bearer_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.auth_jwt_secret:
        raise ValueError("authentication is not configured")

    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("invalid bearer token format")

    encoded_header, encoded_payload, encoded_signature = parts
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")

    header = _decode_segment(encoded_header)
    if header.get("alg") != "HS256":
        raise ValueError("unsupported bearer token algorithm")
    if header.get("typ") not in (None, "JWT"):
        raise ValueError("unsupported bearer token type")

    expected_signature = hmac.new(
        settings.auth_jwt_secret.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    actual_signature = _decode_bytes(encoded_signature)
    if not hmac.compare_digest(actual_signature, expected_signature):
        raise ValueError("invalid bearer token signature")

    payload = _decode_segment(encoded_payload)
    if payload.get("iss") != settings.auth_jwt_issuer:
        raise ValueError("invalid bearer token issuer")

    audience = payload.get("aud")
    valid_audience = settings.auth_jwt_audience
    if isinstance(audience, list):
        if valid_audience not in audience:
            raise ValueError("invalid bearer token audience")
    elif audience != valid_audience:
        raise ValueError("invalid bearer token audience")

    exp = payload.get("exp")
    if exp is not None:
        if not isinstance(exp, int):
            raise ValueError("invalid bearer token expiration")
        if exp < int(time.time()):
            raise ValueError("bearer token has expired")

    return payload


def _decode_segment(encoded_value: str) -> dict[str, Any]:
    decoded = _decode_bytes(encoded_value)
    try:
        return json.loads(decoded.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid bearer token payload") from exc


def _decode_bytes(encoded_value: str) -> bytes:
    padding = "=" * (-len(encoded_value) % 4)
    try:
        return base64.urlsafe_b64decode(encoded_value + padding)
    except Exception as exc:  # pragma: no cover - stdlib raises binascii.Error
        raise ValueError("invalid bearer token encoding") from exc


def _raise_unauthorized(resource: str, detail: str) -> Any:
    audit_log_access(
        "access.denied",
        role="anonymous",
        resource=resource,
        outcome="denied",
        detail=detail,
    )
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
