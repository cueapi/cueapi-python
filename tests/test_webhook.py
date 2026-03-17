"""Tests for webhook signature verification."""

import hashlib
import hmac
import json
import time

import pytest

from cueapi import verify_webhook


def _sign(payload: dict, secret: str) -> tuple:
    """Generate a valid signature matching CueAPI's signing logic."""
    timestamp = str(int(time.time()))
    payload_bytes = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    signed_content = f"{timestamp}.".encode("utf-8") + payload_bytes
    digest = hmac.new(
        secret.encode("utf-8"), signed_content, hashlib.sha256
    ).hexdigest()
    return timestamp, f"v1={digest}"


class TestVerifyWebhook:
    def test_valid_signature_dict(self):
        payload = {"execution_id": "exec_123", "cue_id": "cue_456"}
        secret = "whsec_test_secret"
        timestamp, signature = _sign(payload, secret)

        assert verify_webhook(
            payload=payload,
            signature=signature,
            secret=secret,
            timestamp=timestamp,
        )

    def test_valid_signature_bytes(self):
        payload = {"execution_id": "exec_123", "cue_id": "cue_456"}
        secret = "whsec_test_secret"
        timestamp, signature = _sign(payload, secret)
        payload_bytes = json.dumps(payload).encode("utf-8")

        assert verify_webhook(
            payload=payload_bytes,
            signature=signature,
            secret=secret,
            timestamp=timestamp,
        )

    def test_valid_signature_string(self):
        payload = {"execution_id": "exec_123", "cue_id": "cue_456"}
        secret = "whsec_test_secret"
        timestamp, signature = _sign(payload, secret)
        payload_str = json.dumps(payload)

        assert verify_webhook(
            payload=payload_str,
            signature=signature,
            secret=secret,
            timestamp=timestamp,
        )

    def test_wrong_secret_fails(self):
        payload = {"execution_id": "exec_123"}
        secret = "whsec_correct"
        timestamp, signature = _sign(payload, secret)

        assert not verify_webhook(
            payload=payload,
            signature=signature,
            secret="whsec_wrong",
            timestamp=timestamp,
        )

    def test_tampered_payload_fails(self):
        payload = {"execution_id": "exec_123"}
        secret = "whsec_test"
        timestamp, signature = _sign(payload, secret)

        assert not verify_webhook(
            payload={"execution_id": "exec_TAMPERED"},
            signature=signature,
            secret=secret,
            timestamp=timestamp,
        )

    def test_expired_timestamp_fails(self):
        payload = {"execution_id": "exec_123"}
        secret = "whsec_test"
        old_timestamp = str(int(time.time()) - 600)  # 10 minutes ago
        payload_bytes = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        signed_content = f"{old_timestamp}.".encode("utf-8") + payload_bytes
        digest = hmac.new(
            secret.encode("utf-8"), signed_content, hashlib.sha256
        ).hexdigest()
        signature = f"v1={digest}"

        assert not verify_webhook(
            payload=payload,
            signature=signature,
            secret=secret,
            timestamp=old_timestamp,
        )

    def test_invalid_timestamp_fails(self):
        assert not verify_webhook(
            payload={"test": True},
            signature="v1=abc",
            secret="secret",
            timestamp="not_a_number",
        )

    def test_signature_format_v1(self):
        """Verify we use v1= prefix, NOT sha256= prefix."""
        payload = {"test": True}
        secret = "whsec_test"
        timestamp, signature = _sign(payload, secret)

        assert signature.startswith("v1=")
        assert not signature.startswith("sha256=")
