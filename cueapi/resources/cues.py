"""Cues resource — CRUD operations for CueAPI cues."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from cueapi.exceptions import BodyVerifyMismatchError, first_divergence_byte
from cueapi.models.cue import Cue, CueList

if TYPE_CHECKING:
    from cueapi.client import CueAPI

# Phase 2 of body-verify defense in depth (Mike directive 2026-05-11).
# Substrate echoes the request body bytes back in body_received (str)
# + body_received_sha256 (64-hex SHA256 of the same bytes) when the
# X-CueAPI-Verify-Echo: true request header is set. Field names locked
# during joint design (CMA + cueapi-primary) on Dock workspace
# cue-message-silent-corruption-substrate-design-2026-05-11.
_VERIFY_ECHO_BODY_FIELD = "body_received"
_VERIFY_ECHO_SHA256_FIELD = "body_received_sha256"


class CuesResource:
    """Manage cues (scheduled tasks)."""

    def __init__(self, client: CueAPI) -> None:
        self._client = client

    def create(
        self,
        name: str,
        *,
        cron: Optional[str] = None,
        at: Optional[Union[str, datetime]] = None,
        timezone: str = "UTC",
        callback: Optional[str] = None,
        callback_method: str = "POST",
        callback_headers: Optional[Dict[str, str]] = None,
        transport: str = "webhook",
        payload: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        retry: Optional[Dict[str, Any]] = None,
        on_failure: Optional[Dict[str, Any]] = None,
    ) -> Cue:
        """Create a new cue.

        Args:
            name: Unique name for the cue.
            cron: Cron expression for recurring schedules (e.g. "0 9 * * *").
            at: ISO 8601 datetime for one-time schedules.
            timezone: IANA timezone (default "UTC").
            callback: Webhook URL to receive execution payloads.
            callback_method: HTTP method for webhook delivery (default "POST").
            callback_headers: Custom headers for webhook delivery.
            transport: "webhook" or "worker" (default "webhook").
            payload: JSON payload delivered with each execution.
            description: Optional description.
            retry: Retry config dict with max_attempts and backoff_minutes.
            on_failure: Failure escalation config (email, webhook, pause).

        Returns:
            The created Cue object.
        """
        # Build schedule
        if cron is not None:
            schedule = {"type": "recurring", "cron": cron, "timezone": timezone}
        elif at is not None:
            at_str = at.isoformat() if isinstance(at, datetime) else at
            schedule = {"type": "once", "at": at_str, "timezone": timezone}
        else:
            raise ValueError("Either 'cron' or 'at' must be provided")

        body: Dict[str, Any] = {
            "name": name,
            "schedule": schedule,
            "transport": transport,
            "payload": payload or {},
        }

        # Callback
        if callback is not None:
            cb: Dict[str, Any] = {"url": callback, "method": callback_method}
            if callback_headers:
                cb["headers"] = callback_headers
            body["callback"] = cb

        if description is not None:
            body["description"] = description
        if retry is not None:
            body["retry"] = retry
        if on_failure is not None:
            body["on_failure"] = on_failure

        data = self._client._post("/v1/cues", json=body)
        return Cue.model_validate(data)

    def list(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> CueList:
        """List cues for the authenticated user.

        Args:
            limit: Max cues to return (default 20, max 100).
            offset: Pagination offset.
            status: Filter by status ("active" or "paused").

        Returns:
            CueList with cues, total, limit, offset.
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if status is not None:
            params["status"] = status
        data = self._client._get("/v1/cues", params=params)
        return CueList.model_validate(data)

    def get(self, cue_id: str) -> Cue:
        """Get a cue by ID.

        Args:
            cue_id: The cue ID (e.g. "cue_abc123").

        Returns:
            The Cue object.
        """
        data = self._client._get(f"/v1/cues/{cue_id}")
        return Cue.model_validate(data)

    def update(
        self,
        cue_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        cron: Optional[str] = None,
        at: Optional[Union[str, datetime]] = None,
        timezone: Optional[str] = None,
        callback: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        retry: Optional[Dict[str, Any]] = None,
        on_failure: Optional[Dict[str, Any]] = None,
    ) -> Cue:
        """Update a cue.

        Only provided fields are updated. Omitted fields are unchanged.

        Args:
            cue_id: The cue ID to update.
            name: New name.
            description: New description.
            status: "active" or "paused".
            cron: New cron expression (changes to recurring schedule).
            at: New one-time datetime.
            timezone: New timezone.
            callback: New callback URL.
            payload: New payload.
            retry: New retry config.
            on_failure: New failure escalation config.

        Returns:
            The updated Cue object.
        """
        body: Dict[str, Any] = {}

        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if status is not None:
            body["status"] = status
        if payload is not None:
            body["payload"] = payload
        if retry is not None:
            body["retry"] = retry
        if on_failure is not None:
            body["on_failure"] = on_failure

        # Schedule update
        if cron is not None or at is not None:
            schedule: Dict[str, Any] = {}
            if cron is not None:
                schedule["type"] = "recurring"
                schedule["cron"] = cron
            elif at is not None:
                schedule["type"] = "once"
                schedule["at"] = at.isoformat() if isinstance(at, datetime) else at
            if timezone is not None:
                schedule["timezone"] = timezone
            body["schedule"] = schedule

        if callback is not None:
            body["callback"] = {"url": callback}

        data = self._client._patch(f"/v1/cues/{cue_id}", json=body)
        return Cue.model_validate(data)

    def delete(self, cue_id: str) -> None:
        """Delete a cue.

        Args:
            cue_id: The cue ID to delete.
        """
        self._client._delete(f"/v1/cues/{cue_id}")

    def bulk_delete(self, ids: List[str]) -> Dict[str, List[str]]:
        """Delete multiple cues in a single call (max 100 per call).

        Per-ID atomic, NOT batch atomic — each ID is independently checked
        for caller ownership. IDs that don't exist OR aren't owned by the
        caller land in the ``skipped`` array (silent skip on miss; no
        info leak about other tenants' cues). Cascade FK handles
        executions + dispatch_outbox cleanup.

        Sends the ``X-Confirm-Destructive: true`` header automatically;
        the substrate requires it for any bulk-destructive endpoint.

        Args:
            ids: Cue IDs to delete. Length 1-100. Server enforces the cap;
                this method also validates client-side to fail fast.

        Returns:
            A dict shaped::

                {
                    "deleted": ["cue_abc", "cue_def"],   # IDs whose rows are gone
                    "skipped": ["cue_xyz"]               # IDs that didn't exist or weren't owned
                }

            Order within each group preserves the request's ``ids`` array.

        Raises:
            ValueError: If ``ids`` is empty or has more than 100 entries.

        Example:
            >>> client.cues.bulk_delete(["cue_abc", "cue_def", "cue_xyz"])
            {"deleted": ["cue_abc", "cue_def"], "skipped": ["cue_xyz"]}
        """
        if not ids:
            raise ValueError("ids must contain at least one cue ID.")
        if len(ids) > 100:
            raise ValueError(
                f"Max 100 IDs per call; got {len(ids)}. Split into batches."
            )
        return self._client._post(
            "/v1/cues/bulk-delete",
            json={"ids": list(ids)},
            headers={"X-Confirm-Destructive": "true"},
        )

    def pause(self, cue_id: str) -> Cue:
        """Pause a cue. Equivalent to update(cue_id, status="paused").

        Args:
            cue_id: The cue ID to pause.

        Returns:
            The updated Cue object.
        """
        return self.update(cue_id, status="paused")

    def resume(self, cue_id: str) -> Cue:
        """Resume a paused cue. Equivalent to update(cue_id, status="active").

        Args:
            cue_id: The cue ID to resume.

        Returns:
            The updated Cue object.
        """
        return self.update(cue_id, status="active")

    def fire(
        self,
        cue_id: str,
        *,
        payload_override: Optional[Dict[str, Any]] = None,
        merge_strategy: Optional[str] = None,
        send_at: Optional[Union[str, datetime]] = None,
        exit_criteria: Optional[List[str]] = None,
        idempotency_key: Optional[str] = None,
        auto_verify: bool = False,
    ) -> Dict[str, Any]:
        """Fire an existing cue, optionally overriding payload + scheduling.

        ``POST /v1/cues/{cue_id}/fire``. Returns the created execution
        dict (not a Cue) — fire creates an execution row, not a new cue.

        Useful for ad-hoc one-shot triggers and for using cues as a
        messaging channel between agents (carry message/instruction/task/
        reply_cue_id in ``payload_override``).

        Args:
            cue_id: The cue ID to fire.
            payload_override: Override the cue's default payload for this
                fire only. Persisted on the resulting execution row, never
                on the cue itself.
            merge_strategy: How ``payload_override`` combines with the
                cue's stored payload. ``"merge"`` (server default) shallow-
                merges with override wins on key collisions. ``"replace"``
                uses override as the final payload, ignoring ``cue.payload``.
            send_at: Optional ISO 8601 timestamp (or ``datetime``) to
                delay this fire. If omitted, the execution is scheduled
                immediately. Per-fire scheduling landed in cueapi #618.
            exit_criteria: Optional list of required-assertion keys for
                §14 work-verification-light (cueapi #632). When non-null,
                the receiver MUST report values for every key under
                ``outcome.assertions``; missing keys mark the execution
                ``verification_failed``. Empty list (``[]``) explicitly
                opts out of cue-level required_assertions for this fire.
                None = use cue-level (existing behavior). Max 20 keys.
            idempotency_key: Optional opaque caller-supplied dedup key
                (cueapi #683, ≤256 chars). Same key on the same cue
                within 24h returns the cached execution without firing
                again (matched by SHA-256 fingerprint of the canonicalized
                body). Same key + DIFFERENT body in the window returns
                409 ``idempotency_key_conflict``. Sent as a body field
                (NOT the ``Idempotency-Key`` header — server-side cues
                fire diverges from messaging-primitive convention here;
                Phase 2 spec puts it in the body).

        Returns:
            The execution dict (id, scheduled_for, status, triggered_by,
            etc.).

        Examples:
            >>> exec = client.cues.fire("cue_abc123")
            >>> exec = client.cues.fire(
            ...     "cue_abc123",
            ...     payload_override={"task": "manual-trigger"},
            ...     send_at="2026-05-07T12:00:00Z",
            ...     exit_criteria=["task_completed", "result_valid"],
            ...     idempotency_key="ci-run-456",
            ... )
        """
        body: Dict[str, Any] = {}
        if payload_override is not None:
            body["payload_override"] = payload_override
        if merge_strategy is not None:
            body["merge_strategy"] = merge_strategy
        if send_at is not None:
            body["send_at"] = (
                send_at.isoformat() if isinstance(send_at, datetime) else send_at
            )
        if exit_criteria is not None:
            body["exit_criteria"] = exit_criteria
        # idempotency_key is a body field on cues fire (server's
        # FireRequest schema), unlike messaging-primitive idempotency
        # which uses the Idempotency-Key header. Server-side
        # inconsistency that the SDK has to live with.
        if idempotency_key is not None:
            body["idempotency_key"] = idempotency_key

        # Phase 2 of body-verify defense in depth (Mike directive 2026-05-11).
        # Substrate echoes request body bytes back as body_received (str) +
        # body_received_sha256 (64-hex SHA256) when X-CueAPI-Verify-Echo:
        # true header is set. We compute the same SHA256 client-side over
        # our request body JSON + compare hex (constant cost) — falls back
        # to string compare on body_received string if available. Mirrors
        # MessagesResource.send auto_verify pattern.
        headers: Dict[str, str] = {}
        sent_body_bytes: Optional[bytes] = None
        if auto_verify:
            headers["X-CueAPI-Verify-Echo"] = "true"
            # Pre-compute canonical JSON bytes for the verify-echo
            # comparison. Server hashes the body bytes it received;
            # this client hashes the body bytes we send. Match should
            # be byte-identical if no transport-layer mutation occurred.
            sent_body_bytes = json.dumps(body, separators=(",", ":")).encode("utf-8")

        response = self._client._post(
            f"/v1/cues/{cue_id}/fire", json=body, headers=headers
        )

        # Verify echo if requested. Defensive isinstance handles both
        # current substrate (flat string post-fix 2026-05-11 ~23:48Z)
        # and the earlier dict-shape variant + the no-echo backward-
        # compat path.
        if auto_verify and isinstance(response, dict) and sent_body_bytes is not None:
            received_raw = response.get(_VERIFY_ECHO_BODY_FIELD)
            received_str: Optional[str] = None
            if isinstance(received_raw, str):
                received_str = received_raw
            elif isinstance(received_raw, dict):
                # Pre-fix wire shape: serialize for compare. Future-
                # proof in case any deployment still ships the dict.
                received_str = json.dumps(received_raw, separators=(",", ":"))

            # Prefer constant-cost SHA256 comparison when both server +
            # client compute the same digest. Falls back to string
            # compare if the sha field is absent.
            sha_field = response.get(_VERIFY_ECHO_SHA256_FIELD)
            mismatch_detected = False
            if isinstance(sha_field, str) and len(sha_field) == 64:
                # Server's sha256 hashes the raw request bytes it
                # received. We compute over our locally-serialized
                # bytes. JSON-canonicalization differences (key order,
                # whitespace) could cause spurious mismatch — so on
                # sha mismatch, fall back to string-compare which is
                # more forgiving on serialization differences.
                client_sha = hashlib.sha256(sent_body_bytes).hexdigest()
                if client_sha != sha_field:
                    # SHA mismatch — verify with string compare; if THAT
                    # also fails, it's a real divergence.
                    if received_str is not None and received_str != json.dumps(
                        body, separators=(",", ":")
                    ):
                        mismatch_detected = True
            else:
                # No sha field; compare body_received string vs our
                # canonical body JSON.
                if received_str is not None and received_str != json.dumps(
                    body, separators=(",", ":")
                ):
                    mismatch_detected = True

            if mismatch_detected and received_str is not None:
                exec_id = response.get("id", "<unknown>")
                sent_str = json.dumps(body, separators=(",", ":"))
                divergence = first_divergence_byte(sent_str, received_str)
                if divergence == -1 and len(sent_str) != len(received_str):
                    divergence = min(len(sent_str), len(received_str))
                raise BodyVerifyMismatchError(
                    f"Cue fire body received by substrate ({len(received_str)} bytes) differs "
                    f"from body sent ({len(sent_str)} bytes); first divergence at byte "
                    f"{divergence}. Likely cause: caller-side mutation of payload_override or "
                    f"send_at fields before reaching the SDK. Inspect the dict you constructed.",
                    sent_body=sent_str,
                    received_body=received_str,
                    first_divergence_byte=divergence,
                    message_id=exec_id,  # execution id for fire (NOT message id)
                )
        return response
