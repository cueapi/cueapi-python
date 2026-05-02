"""Executions resource — outcome reporting, listing, and verification."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from cueapi.client import CueAPI


class ExecutionContext:
    """Context manager for auto-reporting outcomes."""

    def __init__(self, resource: ExecutionsResource, execution_id: str, payload: dict = None):
        self._resource = resource
        self.execution_id = execution_id
        self.payload = payload or {}
        self.result = None
        self.error = None
        self.evidence = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Exception -> report failure
            self._resource.report_outcome(
                self.execution_id,
                success=False,
                error=str(exc_val)[:2000],
            )
            return False  # Don't suppress the exception
        else:
            # Clean exit -> report success
            kwargs: Dict[str, Any] = {"success": True}
            if self.result:
                kwargs["result"] = str(self.result)[:2000]
            if self.evidence:
                kwargs.update(self.evidence)
            self._resource.report_outcome(self.execution_id, **kwargs)
            return False


class ExecutionsResource:
    """Executions API resource."""

    def __init__(self, client: CueAPI) -> None:
        self._client = client

    def report_outcome(
        self,
        execution_id: str,
        *,
        success: bool,
        result: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[dict] = None,
        external_id: Optional[str] = None,
        result_url: Optional[str] = None,
        result_ref: Optional[str] = None,
        result_type: Optional[str] = None,
        summary: Optional[str] = None,
        artifacts: Optional[list] = None,
    ) -> dict:
        """Report outcome for an execution."""
        body: Dict[str, Any] = {"success": success}
        if result is not None:
            body["result"] = result
        if error is not None:
            body["error"] = error
        if metadata is not None:
            body["metadata"] = metadata
        if external_id is not None:
            body["external_id"] = external_id
        if result_url is not None:
            body["result_url"] = result_url
        if result_ref is not None:
            body["result_ref"] = result_ref
        if result_type is not None:
            body["result_type"] = result_type
        if summary is not None:
            body["summary"] = summary
        if artifacts is not None:
            body["artifacts"] = artifacts
        return self._client._post(f"/v1/executions/{execution_id}/outcome", json=body)

    def handle(self, execution_id: str, payload: dict = None) -> ExecutionContext:
        """Context manager that auto-reports outcome on exit.

        Usage::

            with client.executions.handle(exec_id) as ctx:
                result = do_work(ctx.payload)
                ctx.result = f"Processed {result.count} records"
            # Clean exit -> auto POST success=True
            # Exception  -> auto POST success=False
        """
        return ExecutionContext(self, execution_id, payload)

    def list(
        self,
        *,
        cue_id: Optional[str] = None,
        status: Optional[str] = None,
        outcome_state: Optional[str] = None,
        triggered_by: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        """List executions with optional filters."""
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if cue_id:
            params["cue_id"] = cue_id
        if status:
            params["status"] = status
        if outcome_state:
            params["outcome_state"] = outcome_state
        if triggered_by:
            params["triggered_by"] = triggered_by
        return self._client._get("/v1/executions", params=params)

    def get(self, execution_id: str) -> dict:
        """Get a single execution."""
        return self._client._get(f"/v1/executions/{execution_id}")

    def list_claimable(
        self,
        *,
        task: Optional[str] = None,
        agent: Optional[str] = None,
    ) -> dict:
        """List unclaimed worker-transport executions ready for processing.

        Filters server-side via task / agent query params (NOT client-side).
        Required for single-purpose workers; without a filter, sibling tasks
        ahead in the LIMIT 50 window starve your handler.

        Returns:
            Dict with "executions" list, each item carrying execution_id,
            cue_id, cue_name, task, scheduled_for, payload, attempt.
        """
        params: Dict[str, Any] = {}
        if task is not None:
            params["task"] = task
        if agent is not None:
            params["agent"] = agent
        return self._client._get("/v1/executions/claimable", params=params)

    def claim(self, execution_id: str, *, worker_id: str) -> dict:
        """Atomically claim a specific worker-transport execution.

        Conditional UPDATE WHERE status IN ('pending', 'retry_ready'); returns
        409 if already claimed or not eligible. Response includes lease_seconds
        (default 900s = 15 min); send heartbeat well before that to extend.

        Args:
            execution_id: Execution UUID.
            worker_id: Stable identifier for this worker. Caller-defined, not
                session/process-scoped. Same value must be used across
                claim, heartbeat, and outcome calls so the server can enforce
                ownership.

        Returns:
            Dict with claimed (bool), execution_id, lease_seconds.
        """
        return self._client._post(
            f"/v1/executions/{execution_id}/claim",
            json={"worker_id": worker_id},
        )

    def claim_next(
        self,
        *,
        worker_id: str,
        task: Optional[str] = None,
    ) -> dict:
        """Claim the next available worker-transport execution.

        Without task, the server picks the oldest pending across any of your
        worker cues. With task, this method internally fans out (list_claimable
        filtered, pick oldest, claim by ID) since the server's claim endpoint
        does not accept a task filter today. Tiny race window between list and
        claim is bounded by the atomic claim returning 409, in which case the
        caller retries.

        Args:
            worker_id: Stable caller-defined identifier (see claim()).
            task: Optional task filter.

        Returns:
            Dict with claimed (bool), execution_id, lease_seconds. When
            task is set and no executions are claimable for that task,
            returns {"claimed": False, "reason": "no_executions_for_task",
            "task": <task>}.
        """
        if task is not None:
            listing = self._client._get(
                "/v1/executions/claimable", params={"task": task}
            )
            execs = listing.get("executions") or []
            if not execs:
                return {
                    "claimed": False,
                    "reason": "no_executions_for_task",
                    "task": task,
                }
            next_id = execs[0].get("execution_id")
            return self._client._post(
                f"/v1/executions/{next_id}/claim",
                json={"worker_id": worker_id},
            )
        return self._client._post(
            "/v1/executions/claim", json={"worker_id": worker_id}
        )

    def heartbeat(self, execution_id: str) -> dict:
        """Send heartbeat to extend claim lease."""
        return self._client._post(f"/v1/executions/{execution_id}/heartbeat", json={})

    def mark_verification_pending(self, execution_id: str) -> dict:
        """Mark execution outcome as pending verification."""
        return self._client._post(
            f"/v1/executions/{execution_id}/verification-pending", json={}
        )

    def mark_verified(
        self,
        execution_id: str,
        *,
        valid: bool = True,
        reason: Optional[str] = None,
    ) -> dict:
        """Mark execution outcome as verified or verification failed."""
        return self._client._post(f"/v1/executions/{execution_id}/verify", json={})
