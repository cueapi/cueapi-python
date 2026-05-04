"""Pydantic models for CueAPI resources."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Schedule(BaseModel):
    type: str
    cron: Optional[str] = None
    at: Optional[datetime] = None
    timezone: str = "UTC"


class Callback(BaseModel):
    url: Optional[str] = None
    method: str = "POST"
    headers: Dict[str, str] = Field(default_factory=dict)


class Retry(BaseModel):
    max_attempts: int = 3
    backoff_minutes: List[int] = Field(default_factory=lambda: [1, 5, 15])


class OnFailure(BaseModel):
    email: bool = True
    webhook: Optional[str] = None
    pause: bool = False


class DeliveryConfig(BaseModel):
    """Two-phase delivery configuration (Gap 5)."""

    timeout_seconds: int = 30
    outcome_deadline_seconds: int = 300


class AlertConfig(BaseModel):
    """Alert configuration (Gap 5).

    Surfaced as a passthrough dict via ``extra="allow"`` so callers see
    every field the server returns even if the SDK hasn't been updated
    for new alert kinds yet. Models that have grown additively benefit
    from forward-compat.
    """

    model_config = {"extra": "allow"}


class VerificationConfig(BaseModel):
    """Outcome verification policy.

    The ``mode`` field controls evidence requirements. The
    ``required_assertions`` field (Gap 8) controls structural requirements
    on the reported outcome.
    """

    mode: Optional[str] = None
    required_assertions: Optional[List[str]] = None
    model_config = {"extra": "allow"}


class Cue(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: str
    transport: str = "webhook"
    schedule: Schedule
    callback: Callback
    payload: Dict[str, Any] = Field(default_factory=dict)
    retry: Retry = Field(default_factory=Retry)
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    run_count: int = 0
    fired_count: int = 0
    on_failure: Optional[OnFailure] = None
    # Two-phase + alerts + catch-up + verification config (hosted Phase
    # 18 / Gap 5 / Gap 8). All optional and forward-compat — server
    # may grow these objects over time without breaking SDK callers.
    delivery: Optional[DeliveryConfig] = None
    alerts: Optional[AlertConfig] = None
    catch_up: Optional[str] = None
    verification: Optional[VerificationConfig] = None
    # On-success chaining (Gap 1): cue ID to fire when an execution of
    # this cue reaches a successful terminal state. Strictly 1:1.
    on_success_fire: Optional[str] = None
    # Per-cue payload_override enforcement on /fire (hosted PR #590).
    # Default false (server's default) so old responses without these
    # keys still parse cleanly.
    require_payload_override: bool = False
    required_payload_keys: Optional[List[str]] = None
    # Cue-detail-response stats: 7d success rate, miss rate, totals.
    # Returned only on GET /v1/cues/{id} detail; absent on list rows.
    stats: Optional[Dict[str, Any]] = None
    warning: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CueList(BaseModel):
    cues: List[Cue]
    total: int
    limit: int
    offset: int
