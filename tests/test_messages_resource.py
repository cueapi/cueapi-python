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

        mock_client._post.assert_called_once_with(
            "/v1/messages",
            json={"to": "recipient@y", "body": "hi"},
            headers={"X-Cueapi-From-Agent": "sender@x"},
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
        # Headers should ONLY contain X-Cueapi-From-Agent when no
        # idempotency_key is passed. Pin so a refactor can't silently
        # start adding `Idempotency-Key: None` (httpx would coerce).
        mock_client = MagicMock()
        mock_client._post.return_value = {"id": "msg_x"}
        r = MessagesResource(mock_client)

        r.send(from_agent="x", to="y", body="hi")

        headers = mock_client._post.call_args.kwargs["headers"]
        assert headers == {"X-Cueapi-From-Agent": "x"}
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
            headers={"X-Cueapi-From-Agent": "sender@x"},
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
