"""Workers resource — fleet visibility for worker-transport users."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cueapi.client import CueAPI


class WorkersResource:
    """Workers API resource.

    Mirrors the hosted ``/v1/workers`` surface — list registered workers
    with heartbeat status, and delete decommissioned workers. Worker
    registration itself happens via cueapi-worker (which sends heartbeats);
    the SDK doesn't expose ``POST /v1/worker/heartbeat`` because direct
    SDK-driven registration is redundant with that package.
    """

    def __init__(self, client: "CueAPI") -> None:
        self._client = client

    def list(self) -> dict:
        """List all registered workers with heartbeat status.

        Returns:
            Dict with ``workers`` (list of worker dicts) and ``total``.
            Each worker carries ``worker_id``, ``handlers``,
            ``last_heartbeat``, ``heartbeat_status``
            (``online`` / ``stale`` / ``dead`` based on seconds since
            last heartbeat), and ``seconds_since_heartbeat``.
        """
        return self._client._get("/v1/workers")

    def delete(self, worker_id: str) -> None:
        """Delete a registered worker.

        Removes the worker row; in-flight executions claimed by this
        worker will be picked up by the stale-recovery loop. Useful for
        cleaning up workers that have been decommissioned.

        Returns ``None`` on success (HTTP 204). Raises
        ``CueNotFoundError`` if the worker doesn't exist.

        Args:
            worker_id: The caller-defined worker_id used during the
                worker's heartbeats. Same value is what appears in
                ``list()`` responses.
        """
        return self._client._delete(f"/v1/workers/{worker_id}")
