"""Agents resource — messaging primitive identity surface (Phase 12.1.5)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from cueapi.client import CueAPI


class AgentsResource:
    """Agents API resource.

    Wraps the ``/v1/agents`` surface from the messaging primitive
    (Phase 12.1.5). Covers identity CRUD, webhook-secret rotation, and
    the inbox/sent message lists keyed by agent ref.

    The send/get/read/ack message lifecycle lives on a sibling
    ``client.messages`` resource — this class only handles identity.
    """

    def __init__(self, client: "CueAPI") -> None:
        self._client = client

    def create(
        self,
        *,
        display_name: str,
        slug: Optional[str] = None,
        webhook_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """Create an agent.

        The ``webhook_secret`` field is populated in the 201 response
        ONLY when ``webhook_url`` is supplied. Subsequent reads omit
        the secret. Save it now or use ``webhook_secret_regenerate()``
        to mint a fresh one (which revokes the old one).

        Args:
            display_name: Human-readable name (1-255 chars).
            slug: Optional per-user unique slug. If omitted, the server
                derives one from ``display_name``.
            webhook_url: Push-delivery target. SSRF-validated. Omit for
                poll-only.
            metadata: Optional JSON metadata blob.

        Returns:
            Dict matching the server's ``AgentResponse`` shape, including
            ``webhook_secret`` ONCE on this response if ``webhook_url``
            was given.
        """
        body: Dict[str, Any] = {"display_name": display_name}
        if slug is not None:
            body["slug"] = slug
        if webhook_url is not None:
            body["webhook_url"] = webhook_url
        if metadata is not None:
            body["metadata"] = metadata
        return self._client._post("/v1/agents", json=body)

    def list(
        self,
        *,
        status: Optional[str] = None,
        include_deleted: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """List your agents.

        Args:
            status: Optional filter — ``online`` / ``offline`` / ``away``.
            include_deleted: Whether to include soft-deleted agents.
                Defaults to False; only sent on the wire when True
                (omit-when-default keeps URLs clean and matches the
                server's ``include_deleted=false`` default).
            limit: Page size (default 50, max 100).
            offset: Pagination offset.
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if status is not None:
            params["status"] = status
        if include_deleted:
            params["include_deleted"] = "true"
        return self._client._get("/v1/agents", params=params)

    def get(
        self,
        ref: str,
        *,
        include_deleted: bool = False,
    ) -> dict:
        """Get an agent by opaque ID or slug-form (``agent@user``)."""
        params: Dict[str, Any] = {}
        if include_deleted:
            params["include_deleted"] = "true"
        return self._client._get(f"/v1/agents/{ref}", params=params)

    def update(
        self,
        ref: str,
        *,
        display_name: Optional[str] = None,
        webhook_url: Optional[str] = None,
        clear_webhook_url: bool = False,
        status: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """Update an agent (PATCH semantics).

        ``webhook_url`` and ``clear_webhook_url`` are mutually exclusive.
        Pass ``clear_webhook_url=True`` to send literal JSON ``null`` and
        revert the agent to poll-only — the server uses
        ``model_fields_set`` to disambiguate "field omitted = no change"
        from "field explicitly null = clear", so the SDK MUST send the
        key with explicit None rather than omit.
        """
        if webhook_url is not None and clear_webhook_url:
            raise ValueError(
                "webhook_url and clear_webhook_url are mutually exclusive"
            )
        body: Dict[str, Any] = {}
        if display_name is not None:
            body["display_name"] = display_name
        if webhook_url is not None:
            body["webhook_url"] = webhook_url
        elif clear_webhook_url:
            body["webhook_url"] = None
        if status is not None:
            body["status"] = status
        if metadata is not None:
            body["metadata"] = metadata
        return self._client._patch(f"/v1/agents/{ref}", json=body)

    def delete(self, ref: str) -> None:
        """Soft-delete an agent. Returns ``None`` on success (204)."""
        return self._client._delete(f"/v1/agents/{ref}")

    def webhook_secret_get(self, ref: str) -> dict:
        """Reveal the agent's current webhook signing secret.

        404 path commonly means the agent has no ``webhook_url`` set
        (poll-only agents have no webhook secret).
        """
        return self._client._get(f"/v1/agents/{ref}/webhook-secret")

    def webhook_secret_regenerate(self, ref: str) -> dict:
        """Mint a fresh webhook secret. Old secret revoked immediately.

        Sends ``X-Confirm-Destructive: true`` header, which the server
        requires for this destructive op. Returns the new secret one-time
        in the response — save it now.
        """
        return self._client._post(
            f"/v1/agents/{ref}/webhook-secret/regenerate",
            json={},
            headers={"X-Confirm-Destructive": "true"},
        )

    def inbox(
        self,
        ref: str,
        *,
        state: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """Poll the agent's inbox (incoming messages).

        Args:
            ref: Agent opaque ID or slug-form.
            state: Optional filter (e.g. ``queued`` / ``delivered`` /
                ``read`` / ``acked`` / ``failed``).
            limit: Page size (default 50).
            offset: Pagination offset.
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if state is not None:
            params["state"] = state
        return self._client._get(f"/v1/agents/{ref}/inbox", params=params)

    def sent(
        self,
        ref: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """List messages sent by this agent."""
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        return self._client._get(f"/v1/agents/{ref}/sent", params=params)

    def roster(
        self,
        *,
        if_none_match: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List the agent directory (Surface 6, cueapi #630).

        Returns the user's agent directory — every agent owned by the
        calling key with a presence block (online state, derived status,
        bucketed last-seen, default-live cue, labeled live sessions).
        Used by Directory v0/v1/v2 UIs and by senders that want to
        choose recipients based on presence.

        Args:
            if_none_match: Optional ETag from a prior call. Server
                returns ``304 Not Modified`` (raised as
                ``CueAPIError`` with status 304) if the directory
                hasn't changed. Use to cheap-poll without re-fetching
                payloads.

        Returns:
            Dict with ``agents`` list (each carrying presence block) and
            ``etag`` for the next call.
        """
        headers: Dict[str, str] = {}
        if if_none_match is not None:
            headers["If-None-Match"] = if_none_match
        kwargs: Dict[str, Any] = {}
        if headers:
            kwargs["headers"] = headers
        return self._client._get("/v1/agents/roster", **kwargs)

    def presence(self, ref: str) -> Dict[str, Any]:
        """Cheap-poll a single agent's presence block (cueapi #662).

        Lighter than ``get(ref)`` — returns just the presence-relevant
        fields (online, derived_status, bucketed_seen, default_live,
        labeled_sessions, etag) without the full agent record.
        Designed for UIs that need to refresh a single tile every few
        seconds without re-fetching the full directory or agent record.

        Args:
            ref: Agent opaque ID (``agt_<12 alnum>``) or slug-form
                (``slug@user``).

        Returns:
            Presence dict.
        """
        return self._client._get(f"/v1/agents/{ref}/presence")

    # ───────────────────────────────────────────────────────────────
    # Event-emit primitive (PR-1b)
    # ───────────────────────────────────────────────────────────────

    def subscriptions_create(
        self,
        ref: str,
        *,
        event_type: str,
        delivery_target: str,
        webhook_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a subscription for an agent (PR-1b event-emit primitive).

        Subscriptions are agent-scoped — an agent can only subscribe to
        events FOR ITSELF. The caller must own the agent.

        Args:
            ref: Agent opaque ID or slug-form (the subscribing agent).
            event_type: The event type to subscribe to (e.g.
                ``message.received``).
            delivery_target: ``"pull"`` (poll via ``events_pull``) or
                ``"webhook"`` (server POSTs to ``webhook_url`` with HMAC).
            webhook_url: Required when ``delivery_target="webhook"``;
                HTTPS only. Ignored for pull subscriptions.

        Returns:
            Subscription dict. For webhook subscriptions, the response
            includes ``webhook_secret`` ONE-TIME — save it now; the
            server never re-exposes it.

        Errors:
            400 ``unknown_event_type`` / ``invalid_delivery_target`` /
            ``invalid_webhook_url``; 404 ``agent_not_found``.
        """
        body: Dict[str, Any] = {
            "event_type": event_type,
            "delivery_target": delivery_target,
        }
        if webhook_url is not None:
            body["webhook_url"] = webhook_url
        return self._client._post(f"/v1/agents/{ref}/subscriptions", json=body)

    def subscriptions_list(self, ref: str) -> Dict[str, Any]:
        """List active subscriptions for an agent (PR-1b).

        ``webhook_url`` is redacted to host-only in the response;
        ``webhook_secret`` is never exposed here (only on create).
        Each entry includes dispatch-state fields
        (``last_dispatched_event_id``, ``consecutive_failures``,
        ``paused_until``, etc).

        Args:
            ref: Agent opaque ID or slug-form.

        Returns:
            Dict with ``subscriptions`` list.
        """
        return self._client._get(f"/v1/agents/{ref}/subscriptions")

    def subscriptions_delete(self, ref: str, subscription_id: str) -> Dict[str, Any]:
        """Soft-detach a subscription (PR-1b). Idempotent.

        Re-DELETE on an already-detached subscription returns 200
        regardless. The server does NOT delete the row — it marks it
        detached so dispatch stops + audit history is preserved.

        Args:
            ref: Agent opaque ID or slug-form (must match the
                subscription's owning agent).
            subscription_id: UUID of the subscription to detach.

        Returns:
            Result dict.
        """
        return self._client._delete(
            f"/v1/agents/{ref}/subscriptions/{subscription_id}"
        )

    def events_pull(
        self,
        ref: str,
        *,
        since: Optional[int] = None,
        limit: int = 100,
        event_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Pull events from the agent's event stream (PR-1b).

        Events are append-only with a monotonic ``id`` (BIGSERIAL).
        Use ``since`` as a cursor: pass the last ``id`` you saw to
        get only events newer than that. Default 0 fetches from the
        beginning.

        Args:
            ref: Agent opaque ID or slug-form.
            since: Cursor — only return events with ``id > since``.
                Default 0 (all events). Pass the highest ``id`` from
                the previous page to continue.
            limit: Page size (default 100, server caps at 1000).
            event_type: Optional filter — only return events of this
                type. Omit for all event types.

        Returns:
            Dict with ``events`` list (each carrying ``id``,
            ``event_type``, ``payload``, ``emitted_at``) and
            ``next_cursor`` (highest ``id`` in this page; pass back as
            ``since`` for the next call).
        """
        params: Dict[str, Any] = {"limit": limit}
        if since is not None:
            params["since"] = since
        if event_type is not None:
            params["event_type"] = event_type
        return self._client._get(f"/v1/agents/{ref}/events", params=params)
