import base64
import hashlib
import hmac
import json
import time
from typing import Any


def encode_token(payload: dict[str, object], *, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = _urlsafe_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _urlsafe_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(
        secret.encode("utf-8"),
        f"{encoded_header}.{encoded_payload}".encode("ascii"),
        hashlib.sha256,
    ).digest()
    encoded_signature = _urlsafe_encode(signature)
    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def auth_headers(
    *,
    role: str | None = None,
    subject: str = "user-1",
    tenant_id: str = "tenant-a",
    include_tenant: bool = True,
    raw_role: str | None = None,
    issuer: str = "epi-engine",
    audience: str = "epi-engine-clients",
    exp_seconds: int = 3600,
    secret: str,
    extra_claims: dict[str, Any] | None = None,
) -> dict[str, str]:
    claims: dict[str, object] = {
        "sub": subject,
        "role": role if raw_role is None else raw_role,
        "iss": issuer,
        "aud": audience,
        "exp": int(time.time()) + exp_seconds,
    }
    if include_tenant:
        claims["tenant_id"] = tenant_id
    if extra_claims:
        claims.update(extra_claims)
    return {"Authorization": f"Bearer {encode_token(claims, secret=secret)}"}


def _urlsafe_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
