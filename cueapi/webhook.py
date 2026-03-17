"""Webhook signature verification for CueAPI."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Union


def verify_webhook(
    payload: Union[bytes, str, dict],
    signature: str,
    secret: str,
    timestamp: str,
    *,
    tolerance: int = 300,
) -> bool:
    """Verify a CueAPI webhook signature.

    CueAPI signs webhook payloads with HMAC-SHA256 using a per-user webhook
    secret. The signature format is ``v1={hex_digest}`` where the signed
    message is ``{timestamp}.{json_payload}``.

    Args:
        payload: The raw request body (bytes, string, or parsed dict).
        signature: The ``X-CueAPI-Signature`` header value.
        secret: Your webhook signing secret.
        timestamp: The ``X-CueAPI-Timestamp`` header value.
        tolerance: Max age of signature in seconds (default 300 = 5 minutes).

    Returns:
        True if the signature is valid and not expired.

    Example::

        from cueapi import verify_webhook

        is_valid = verify_webhook(
            payload=request.body,
            signature=request.headers["X-CueAPI-Signature"],
            timestamp=request.headers["X-CueAPI-Timestamp"],
            secret="whsec_your_secret",
        )
    """
    # Validate timestamp freshness
    try:
        ts = int(timestamp)
    except (ValueError, TypeError):
        return False

    if abs(time.time() - ts) > tolerance:
        return False

    # Normalize payload to sorted JSON bytes
    if isinstance(payload, dict):
        payload_bytes = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    elif isinstance(payload, str):
        # Try to parse and re-serialize for consistent key ordering
        try:
            parsed = json.loads(payload)
            payload_bytes = json.dumps(parsed, sort_keys=True, default=str).encode("utf-8")
        except (json.JSONDecodeError, TypeError):
            payload_bytes = payload.encode("utf-8")
    else:
        # bytes — try to parse and re-serialize
        try:
            parsed = json.loads(payload)
            payload_bytes = json.dumps(parsed, sort_keys=True, default=str).encode("utf-8")
        except (json.JSONDecodeError, TypeError):
            payload_bytes = payload

    # Compute expected signature: v1={hmac_sha256(secret, "timestamp.payload")}
    signed_content = f"{timestamp}.".encode("utf-8") + payload_bytes
    expected = hmac.new(
        secret.encode("utf-8"), signed_content, hashlib.sha256
    ).hexdigest()
    expected_sig = f"v1={expected}"

    return hmac.compare_digest(expected_sig, signature)
