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
    warning: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CueList(BaseModel):
    cues: List[Cue]
    total: int
    limit: int
    offset: int
