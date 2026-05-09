"""Cues resource — CRUD operations for CueAPI cues."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from cueapi.models.cue import Cue, CueList

if TYPE_CHECKING:
    from cueapi.client import CueAPI


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
    ) -> Dict[str, Any]:
        """Fire an existing cue immediately, optionally overriding its payload.

        For ad-hoc one-shot triggers and for using cues as a messaging channel
        between agents (carry message/instruction/task/reply_cue_id in
        payload_override).

        Args:
            cue_id: The cue ID to fire.
            payload_override: Override the cue's default payload for this fire
                only. Persisted on the resulting execution row, never on the
                cue itself.
            merge_strategy: How payload_override combines with the cue's stored
                payload. "merge" (server default) shallow-merges with override
                wins on key collisions. "replace" uses override as the final
                payload, ignoring cue.payload.

        Returns:
            The execution dict (id, scheduled_for, status, etc.).
        """
        body: Dict[str, Any] = {}
        if payload_override is not None:
            body["payload_override"] = payload_override
        if merge_strategy is not None:
            body["merge_strategy"] = merge_strategy
        return self._client._post(f"/v1/cues/{cue_id}/fire", json=body)
