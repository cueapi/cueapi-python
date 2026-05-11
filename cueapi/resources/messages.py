"""Messages resource — messaging primitive lifecycle (Phase 12.1.5)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

from cueapi.exceptions import BodyVerifyMismatchError, first_divergence_byte

if TYPE_CHECKING:
    from cueapi.client import CueAPI

# Response field where Layer 1 substrate echoes back the body it received
# (Phase 2 of body-verify defense in depth; Mike directive 2026-05-11).
# Substrate-side ships this field in the 201 response when the request
# included ``X-CueAPI-Verify-Echo: true`` header. Field name locked
# during joint design between cueapi-primary (substrate) + CMA (SDK);
# update if the design Dock spec finalizes a different name.
_VERIFY_ECHO_FIELD = "body_received"


class MessagesResource:
    """Messages API resource.

    Wraps the ``/v1/messages`` surface from the messaging primitive
    (Phase 12.1.5). Covers send + per-message lifecycle (get / read /
    ack). The agents identity surface lives on the sibling
    ``client.agents`` resource — this class only handles messages.
    """

    def __init__(self, client: "CueAPI") -> None:
        self._client = client

    def send(
        self,
        *,
        from_agent: str,
        to: str,
        body: str,
        subject: Optional[str] = None,
        reply_to: Optional[str] = None,
        priority: Optional[int] = None,
        expects_reply: bool = False,
        reply_to_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
        send_at: Optional[Union[str, datetime]] = None,
        auto_verify: bool = True,
    ) -> dict:
        """Send a message.

        ``from_agent`` is sent as the ``X-Cueapi-From-Agent`` header,
        NOT in the body. The server reads it from the header to
        authenticate the sender against the calling key. Don't try to
        pass it in the body — the server's ``MessageCreate`` schema is
        ``extra="forbid"`` and will 400.

        ``idempotency_key`` is sent as the ``Idempotency-Key`` header.
        Same key + same body within 24h returns the existing message
        with HTTP 200 instead of 201. Same key + different body
        returns HTTP 409 ``idempotency_key_conflict``.

        Args:
            from_agent: Sender agent — opaque agent_id or slug-form
                (``agent@user``). MUST be owned by the calling key.
            to: Recipient — opaque agent_id or slug-form.
            body: Message body (1-32768 chars).
            subject: Optional subject line (max 255 chars).
            reply_to: Previous message ID this is replying to
                (``msg_<12 alphanumeric>``). thread_id inherits.
            priority: 1-5 (server default 3). Receiver-pair limits may
                downgrade priority>3 to 3; the server signals this via
                the ``X-CueAPI-Priority-Downgraded: true`` response
                header. Callers wanting to detect downgrade need to
                inspect the response shape via the underlying
                httpx.Response — not exposed in the SDK return value.
            expects_reply: Mark this message as expecting a reply.
                Default False; only sent when True.
            reply_to_agent: Decoupled reply target. Defaults to
                ``from`` (sender). Use when reply should route to a
                different agent.
            metadata: Optional JSON metadata blob.
            idempotency_key: Optional ``Idempotency-Key`` header
                (≤255 chars).
            send_at: Optional ISO 8601 timestamp (or ``datetime``) to
                delay this message's delivery. If omitted, the message
                is delivered immediately. Per-message scheduling landed
                in cueapi #623 — server stores ``send_at`` on the
                message row and the worker picks it up when due.

        Returns:
            Dict matching the server's ``MessageResponse`` shape.

        Raises:
            ValueError: If ``idempotency_key`` exceeds 255 chars
                (matches the server's hard limit).
        """
        if idempotency_key is not None and len(idempotency_key) > 255:
            raise ValueError("idempotency_key must be ≤255 characters")

        payload: Dict[str, Any] = {"to": to, "body": body}
        if subject is not None:
            payload["subject"] = subject
        if reply_to is not None:
            payload["reply_to"] = reply_to
        if priority is not None:
            payload["priority"] = priority
        # Boolean flag — only send when True. Server default is False;
        # sending `false` is no-op + adds payload noise. Pinned in tests.
        if expects_reply:
            payload["expects_reply"] = True
        if reply_to_agent is not None:
            payload["reply_to_agent"] = reply_to_agent
        if metadata is not None:
            payload["metadata"] = metadata
        if send_at is not None:
            payload["send_at"] = (
                send_at.isoformat() if isinstance(send_at, datetime) else send_at
            )

        headers: Dict[str, str] = {"X-Cueapi-From-Agent": from_agent}
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        if auto_verify:
            # Phase 2 of body-verify defense in depth. When this header is
            # set, the substrate echoes the body it received in the 201
            # response under the ``body_received`` field. SDK then diffs
            # sent vs received + raises BodyVerifyMismatchError on drift.
            # Substrate ignores the header when Layer 1 isn't deployed
            # yet; SDK no-ops on missing response field. Backward-compat.
            headers["X-CueAPI-Verify-Echo"] = "true"

        response = self._client._post("/v1/messages", json=payload, headers=headers)

        # Verify echo if requested. Empirically-locked wire shape (probed
        # 2026-05-11 ~23:17Z): substrate echoes back the PARSED request
        # body as a dict under ``body_received``. To diff the message
        # body specifically, extract ``body_received.body`` (str) and
        # compare against the str the caller sent.
        #
        # Backward-compat: pre-Layer-1 substrate omits ``body_received``
        # entirely → SDK no-ops. Also defensive: if a future substrate
        # rev returns body_received as a flat string (per the original
        # spec text), the .get("body") chain returns None gracefully via
        # the isinstance check, falling through to no-op rather than
        # raising spuriously.
        if auto_verify and isinstance(response, dict):
            received_dict = response.get(_VERIFY_ECHO_FIELD)
            received_body: Optional[str] = None
            if isinstance(received_dict, dict):
                received_body = received_dict.get("body")
            elif isinstance(received_dict, str):
                # Defensive: future substrate rev may flatten the echo.
                received_body = received_dict
            if received_body is not None and received_body != body:
                msg_id = response.get("id", "<unknown>")
                divergence = first_divergence_byte(body, received_body)
                if divergence == -1 and len(body) != len(received_body):
                    divergence = min(len(body), len(received_body))
                raise BodyVerifyMismatchError(
                    f"Body received by substrate ({len(received_body)} bytes) differs from "
                    f"body sent ({len(body)} bytes); first divergence at byte "
                    f"{divergence}. Likely cause: caller-side shell expansion of "
                    f"$(...) / backticks / ${{VAR}} in the body arg before Python "
                    f"received it. Mitigations: pass body via file (Path.read_text) "
                    f"or use --message-file in cueapi-cli.",
                    sent_body=body,
                    received_body=received_body,
                    first_divergence_byte=divergence,
                    message_id=msg_id,
                )
        return response

    def get(self, msg_id: str) -> dict:
        """Get a single message by ID."""
        return self._client._get(f"/v1/messages/{msg_id}")

    def mark_read(self, msg_id: str) -> dict:
        """Mark a message as read.

        Idempotent — calling on already-``read`` returns 200 unchanged.
        Returns 409 (raised as ``CueAPIError``) if the message is in a
        terminal state (``acked`` / ``expired``).
        """
        return self._client._post(f"/v1/messages/{msg_id}/read", json={})

    def ack(self, msg_id: str) -> dict:
        """Acknowledge a message — terminal state, no further transitions."""
        return self._client._post(f"/v1/messages/{msg_id}/ack", json={})
