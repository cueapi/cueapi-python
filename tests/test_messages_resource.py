"""Tests for MessagesResource."""

import pytest
from unittest.mock import MagicMock

from cueapi.resources.messages import MessagesResource


class TestSend:
    def test_minimal_body_and_from_header(self):
        # Pin: --from goes in X-Cueapi-From-Agent HEADER, NOT in body.
        # The server's MessageCreate is extra="forbid" and would 400 on
        # `{"from": "..."}` in the body, but we want this caught at unit
        # test time, not silently at integration.
        mock_client = MagicMock()
        mock_client._post.return_value = {
            "id": "msg_x", "delivery_state": "queued", "thread_id": "thr_x",
        }
        r = MessagesResource(mock_client)

        r.send(from_agent="sender@x", to="recipient@y", body="hi")

        # Phase 2 of body-verify defense in depth (Mike directive 2026-05-11):
        # auto_verify=True is the new default → X-CueAPI-Verify-Echo header
        # always added. Substrate echoes back received body when Layer 1
        # deployed; SDK diffs + raises BodyVerifyMismatchError on drift.
        mock_client._post.assert_called_once_with(
            "/v1/messages",
            json={"to": "recipient@y", "body": "hi"},
            headers={"X-Cueapi-From-Agent": "sender@x", "X-CueAPI-Verify-Echo": "true"},
        )

    def test_with_all_optionals(self):
        mock_client = MagicMock()
        mock_client._post.return_value = {"id": "msg_x", "delivery_state": "queued"}
        r = MessagesResource(mock_client)

        r.send(
            from_agent="sender@x",
            to="recipient@y",
            body="hi",
            subject="re: hello",
            reply_to="msg_abcdef123456",
            priority=5,
            expects_reply=True,
            reply_to_agent="alt@x",
            metadata={"k": "v"},
            idempotency_key="idemp-key-1",
        )

        call = mock_client._post.call_args
        assert call.args == ("/v1/messages",)
        assert call.kwargs["json"] == {
            "to": "recipient@y",
            "body": "hi",
            "subject": "re: hello",
            "reply_to": "msg_abcdef123456",
            "priority": 5,
            "expects_reply": True,
            "reply_to_agent": "alt@x",
            "metadata": {"k": "v"},
        }
        assert call.kwargs["headers"] == {
            "X-Cueapi-From-Agent": "sender@x",
            "Idempotency-Key": "idemp-key-1",
            "X-CueAPI-Verify-Echo": "true",
        }

    def test_omits_expects_reply_when_default(self):
        # Pin: default False MUST NOT appear in body. Server's Pydantic
        # default is False; sending `expects_reply: false` is no-op + adds
        # noise. Refactor that always-sends would slip past the typed
        # server schema but be caught here.
        mock_client = MagicMock()
        mock_client._post.return_value = {"id": "msg_x"}
        r = MessagesResource(mock_client)

        r.send(from_agent="x", to="y", body="hi")

        body = mock_client._post.call_args.kwargs["json"]
        assert "expects_reply" not in body

    def test_idempotency_key_too_long_raises_client_side(self):
        mock_client = MagicMock()
        r = MessagesResource(mock_client)

        with pytest.raises(ValueError, match="255"):
            r.send(
                from_agent="x", to="y", body="hi",
                idempotency_key="x" * 256,
            )
        # Crucially: must NOT have hit the wire.
        mock_client._post.assert_not_called()

    def test_omits_idempotency_key_header_when_unset(self):
        # Headers should ONLY contain X-Cueapi-From-Agent (+ default
        # auto-verify header) when no idempotency_key is passed. Pin so
        # a refactor can't silently start adding `Idempotency-Key: None`
        # (httpx would coerce).
        mock_client = MagicMock()
        mock_client._post.return_value = {"id": "msg_x"}
        r = MessagesResource(mock_client)

        r.send(from_agent="x", to="y", body="hi")

        headers = mock_client._post.call_args.kwargs["headers"]
        assert headers == {"X-Cueapi-From-Agent": "x", "X-CueAPI-Verify-Echo": "true"}
        assert "Idempotency-Key" not in headers


class TestGet:
    def test_get(self):
        mock_client = MagicMock()
        mock_client._get.return_value = {"id": "msg_x"}
        r = MessagesResource(mock_client)

        r.get("msg_x")

        mock_client._get.assert_called_once_with("/v1/messages/msg_x")


class TestMarkRead:
    def test_mark_read(self):
        mock_client = MagicMock()
        mock_client._post.return_value = {"delivery_state": "read"}
        r = MessagesResource(mock_client)

        r.mark_read("msg_x")

        mock_client._post.assert_called_once_with(
            "/v1/messages/msg_x/read", json={},
        )


class TestAck:
    def test_ack(self):
        mock_client = MagicMock()
        mock_client._post.return_value = {"delivery_state": "acked"}
        r = MessagesResource(mock_client)

        r.ack("msg_x")

        mock_client._post.assert_called_once_with(
            "/v1/messages/msg_x/ack", json={},
        )


class TestSendAt:
    """Per-message scheduling via send_at (cueapi #623 parity port).

    Mock-based following the existing pattern in this file. Asserts on
    the request body shape — that's the SDK contract; what the server
    does with it (delay then deliver) is exercised by the server suite.
    """

    def test_send_with_send_at_iso_string(self):
        """send_at as ISO 8601 string flows into the request body verbatim."""
        mock_client = MagicMock()
        mock_client._post.return_value = {"id": "msg_x", "delivery_state": "queued"}
        r = MessagesResource(mock_client)

        r.send(
            from_agent="sender@x",
            to="recipient@y",
            body="hi",
            send_at="2030-01-01T12:00:00Z",
        )

        mock_client._post.assert_called_once_with(
            "/v1/messages",
            json={
                "to": "recipient@y",
                "body": "hi",
                "send_at": "2030-01-01T12:00:00Z",
            },
            headers={"X-Cueapi-From-Agent": "sender@x", "X-CueAPI-Verify-Echo": "true"},
        )

    def test_send_with_send_at_datetime_auto_isoformats(self):
        """send_at as datetime auto-serializes via .isoformat()."""
        from datetime import datetime, timezone

        mock_client = MagicMock()
        mock_client._post.return_value = {"id": "msg_x", "delivery_state": "queued"}
        r = MessagesResource(mock_client)

        r.send(
            from_agent="sender@x",
            to="recipient@y",
            body="hi",
            send_at=datetime(2030, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        )

        call = mock_client._post.call_args
        assert call.kwargs["json"]["send_at"] == "2030-01-01T12:00:00+00:00"

    def test_send_without_send_at_omits_field(self):
        """send_at unset → field NOT present in request body."""
        mock_client = MagicMock()
        mock_client._post.return_value = {"id": "msg_x", "delivery_state": "queued"}
        r = MessagesResource(mock_client)

        r.send(from_agent="sender@x", to="recipient@y", body="hi")

        call = mock_client._post.call_args
        assert "send_at" not in call.kwargs["json"]


class TestLiveFallbackMode:
    """Agent-id-split refactor Layer 4 (cueapi #824) — live_fallback_mode kwarg.

    Per-message override for substrate's Live-fallback semantic. ``live_only``
    queues until the target Live agent's session is actively heartbeating;
    ``fallback_to_background`` falls through to the Live-sibling's BG parent
    when Live is silent. Default-omit when None so wire format matches
    pre-Layer-4 callers; server applies its default
    (``fallback_to_background`` per spec lock 22:11Z 2026-05-12).

    Backlog row cmp2zi9tl001w04jxcxw3ank1 tracks the cueapi-core OSS port;
    hosted accepts; cueapi-core 422 until precursors land (graceful
    degradation).
    """

    def test_live_fallback_mode_omitted_when_none(self):
        """Default None ⇒ field NOT on wire (preserves pre-Layer-4 shape)."""
        from unittest.mock import MagicMock
        from cueapi.resources.messages import MessagesResource

        mock_client = MagicMock()
        mock_client._post.return_value = {"id": "msg_x", "delivery_state": "queued"}
        r = MessagesResource(mock_client)

        r.send(from_agent="sender@x", to="recipient@y", body="hi")

        call = mock_client._post.call_args
        assert "live_fallback_mode" not in call.kwargs["json"]

    def test_live_fallback_mode_live_only_passes_through(self):
        """``live_only`` flows verbatim into the request body."""
        from unittest.mock import MagicMock
        from cueapi.resources.messages import MessagesResource

        mock_client = MagicMock()
        mock_client._post.return_value = {"id": "msg_x", "delivery_state": "queued"}
        r = MessagesResource(mock_client)

        r.send(
            from_agent="sender@x",
            to="recipient@y",
            body="hi",
            live_fallback_mode="live_only",
        )

        mock_client._post.assert_called_once_with(
            "/v1/messages",
            json={
                "to": "recipient@y",
                "body": "hi",
                "live_fallback_mode": "live_only",
            },
            headers={"X-Cueapi-From-Agent": "sender@x", "X-CueAPI-Verify-Echo": "true"},
        )

    def test_live_fallback_mode_fallback_to_background_passes_through(self):
        """``fallback_to_background`` flows verbatim. Explicit-default value
        is wired-out so callers can disambiguate "I explicitly want fallback"
        from "I didn't specify"."""
        from unittest.mock import MagicMock
        from cueapi.resources.messages import MessagesResource

        mock_client = MagicMock()
        mock_client._post.return_value = {"id": "msg_x", "delivery_state": "queued"}
        r = MessagesResource(mock_client)

        r.send(
            from_agent="sender@x",
            to="recipient@y",
            body="hi",
            live_fallback_mode="fallback_to_background",
        )

        call = mock_client._post.call_args
        assert call.kwargs["json"]["live_fallback_mode"] == "fallback_to_background"


class TestAutoVerify:
    """Phase 2 of body-verify defense in depth (Mike directive 2026-05-11).

    auto_verify=True (default) adds X-CueAPI-Verify-Echo: true header.
    Substrate echoes back received body in 201 response under
    body_received field; SDK diffs sent vs received + raises
    BodyVerifyMismatchError on drift.
    """

    def test_default_adds_verify_echo_header(self):
        mock_client = MagicMock()
        mock_client._post.return_value = {"id": "msg_x", "delivery_state": "queued"}
        r = MessagesResource(mock_client)

        r.send(from_agent="x", to="y", body="hi")

        headers = mock_client._post.call_args.kwargs["headers"]
        assert headers.get("X-CueAPI-Verify-Echo") == "true"

    def test_opt_out_omits_header(self):
        mock_client = MagicMock()
        mock_client._post.return_value = {"id": "msg_x", "delivery_state": "queued"}
        r = MessagesResource(mock_client)

        r.send(from_agent="x", to="y", body="hi", auto_verify=False)

        headers = mock_client._post.call_args.kwargs["headers"]
        assert "X-CueAPI-Verify-Echo" not in headers

    def test_byte_identical_response_returns_normally(self):
        """body_received.body matches sent body → success.

        Empirically-locked wire shape (probed 2026-05-11 ~23:17Z):
        substrate echoes back PARSED request body as dict under
        ``body_received``, NOT a flat string. SDK extracts
        ``body_received.body`` to compare against sent body.
        """
        mock_client = MagicMock()
        mock_client._post.return_value = {
            "id": "msg_x",
            "delivery_state": "queued",
            "body_received": {"to": "y", "body": "hi", "subject": None, "priority": 3},
        }
        r = MessagesResource(mock_client)

        result = r.send(from_agent="x", to="y", body="hi")

        assert result["id"] == "msg_x"

    def test_raises_on_body_mismatch(self):
        """body_received.body differs from sent body → raises BodyVerifyMismatchError."""
        from cueapi.exceptions import BodyVerifyMismatchError

        mock_client = MagicMock()
        mock_client._post.return_value = {
            "id": "msg_mutated",
            "delivery_state": "queued",
            "body_received": {
                "to": "y",
                "body": "body with INJECT (caller's shell command-substituted)",
                "subject": None,
                "priority": 3,
            },
        }
        r = MessagesResource(mock_client)

        with pytest.raises(BodyVerifyMismatchError) as exc:
            r.send(
                from_agent="x", to="y",
                body="body with $(echo INJECT) (intended literal)",
            )

        assert exc.value.message_id == "msg_mutated"
        assert "$(echo INJECT)" in exc.value.sent_body
        assert "INJECT (caller" in exc.value.received_body
        assert exc.value.first_divergence_byte >= 0

    def test_no_op_when_substrate_omits_echo_field(self):
        """Backward-compat: pre-Layer-1 substrate doesn't include
        body_received field → SDK doesn't raise; returns normally."""
        mock_client = MagicMock()
        mock_client._post.return_value = {"id": "msg_x", "delivery_state": "queued"}
        r = MessagesResource(mock_client)

        result = r.send(from_agent="x", to="y", body="hi")

        assert result["id"] == "msg_x"

    def test_opt_out_skips_verify_even_if_substrate_echoes(self):
        """auto_verify=False: even if substrate sends body_received, don't check."""
        mock_client = MagicMock()
        mock_client._post.return_value = {
            "id": "msg_x",
            "body_received": {"to": "y", "body": "DIFFERENT BODY"},
        }
        r = MessagesResource(mock_client)

        result = r.send(from_agent="x", to="y", body="hi", auto_verify=False)

        assert result["id"] == "msg_x"

    def test_defensive_accepts_flat_string_body_received(self):
        """Defensive: if a future substrate rev flattens body_received
        back to a string (per the original spec wording), SDK still
        verifies correctly. Belt + suspenders for spec drift."""
        mock_client = MagicMock()
        mock_client._post.return_value = {
            "id": "msg_x",
            "body_received": "hi",  # flat-string variant
        }
        r = MessagesResource(mock_client)

        result = r.send(from_agent="x", to="y", body="hi")

        assert result["id"] == "msg_x"


class TestFirstDivergenceByte:
    """Pure helper for diagnostic byte-position-of-first-difference."""

    def test_equal_strings_return_minus_one(self):
        from cueapi.exceptions import first_divergence_byte
        assert first_divergence_byte("abc", "abc") == -1

    def test_prefix_returns_minus_one(self):
        from cueapi.exceptions import first_divergence_byte
        assert first_divergence_byte("abc", "abcd") == -1  # one is prefix of other

    def test_first_char_diff(self):
        from cueapi.exceptions import first_divergence_byte
        assert first_divergence_byte("Xbc", "abc") == 0

    def test_middle_diff(self):
        from cueapi.exceptions import first_divergence_byte
        assert first_divergence_byte("abXd", "abcd") == 2

    def test_metachar_substitution_scenario(self):
        """Realistic case: caller's shell substituted $(echo X) → 'X'.

        Sent:     'pre $(echo INJ) post'  (caller intended literal)
        Received: 'pre INJ post'           (shell already substituted)
        First divergence at byte 4 (start of '$' in sent vs 'I' in received).
        """
        from cueapi.exceptions import first_divergence_byte
        sent = "pre $(echo INJ) post"
        received = "pre INJ post"
        assert first_divergence_byte(sent, received) == 4
