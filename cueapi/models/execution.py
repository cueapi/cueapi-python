"""Execution Pydantic model — typed accessor for execution dict responses.

Closes the Execution portion of cueapi-python #24's `model_drift` manifest.
``ExecutionsResource`` methods (`list`, `get`, `replay`) currently return
raw dicts; callers can opt into typed accessors via
``Execution.model_validate(client.executions.get(...))``. Returning the
typed object directly from resource methods is a separate breaking-change
PR (would bump major version).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class OutcomeDetail(BaseModel):
    """Outcome reported by the worker / handler. Set when the execution
    has reached a terminal state and the handler has reported via
    ``POST /v1/executions/{id}/outcome``."""

    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    recorded_at: Optional[datetime] = None
    # Evidence fields (Phase 18 Gap 11 — outcome verification).
    external_id: Optional[str] = None
    result_url: Optional[str] = None
    result_ref: Optional[str] = None
    result_type: Optional[str] = None
    summary: Optional[str] = None
    artifacts: Optional[List[Any]] = None
    validation_state: Optional[str] = None
    assertions: Optional[Dict[str, Any]] = None
    model_config = {"extra": "allow"}


class Execution(BaseModel):
    """Typed accessor for an execution response.

    Mirrors the server's ``ExecutionResponse`` schema. Use as
    ``Execution.model_validate(client.executions.get(exec_id))`` or
    ``Execution.model_validate(item)`` over each item in
    ``client.executions.list()['executions']``.
    """

    id: str
    cue_id: str
    scheduled_for: datetime
    status: str
    http_status: Optional[int] = None
    response_body: Optional[str] = None
    attempts: Optional[int] = None
    next_retry: Optional[datetime] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    last_attempt_at: Optional[datetime] = None
    claimed_by_worker: Optional[str] = None
    claimed_at: Optional[datetime] = None
    last_heartbeat_at: Optional[datetime] = None
    # Hosted PR #589: effective payload the handler/webhook saw at delivery.
    # `payload_override` if set on the execution, else parent cue's payload.
    payload: Optional[Dict[str, Any]] = None
    # Outcome — populated only after handler reports.
    outcome: Optional[OutcomeDetail] = None
    outcome_state: Optional[str] = Field(
        default=None,
        description=(
            "Phase 18 Gap 11: enum tracking outcome verification state. "
            "Values: reported_success / reported_failure / verified_success / "
            "verification_pending / verification_failed / unknown."
        ),
    )
    triggered_by: Optional[str] = Field(
        default=None,
        description="scheduled / manual_fire / chain / replay",
    )
    # Chain support (Gap 1 — on_success_fire native chaining).
    chain_parent_id: Optional[str] = None
    chain_depth: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Forward-compat: server may grow the response over time without the
    # SDK breaking. Same pattern as AlertConfig / VerificationConfig in
    # the Cue model.
    model_config = {"extra": "allow"}


class ExecutionList(BaseModel):
    """Typed accessor for ``client.executions.list()`` responses."""

    executions: List[Execution]
    total: int
    limit: int
    offset: int
    model_config = {"extra": "allow"}
