"""Worker Pydantic model — typed accessor for worker dict responses.

Closes the Worker portion of cueapi-python #24's `model_drift` manifest.
``WorkersResource.list()`` currently returns a raw dict; callers can opt
into typed accessors via ``Worker.model_validate(item)`` over each item
in ``client.workers.list()['workers']``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel


class Worker(BaseModel):
    """Typed accessor for a registered worker.

    Mirrors the server's ``Worker`` model. ``heartbeat_status`` is
    computed server-side from ``seconds_since_heartbeat``:
    - ``online``: <60s since last heartbeat
    - ``stale``: 60-360s since last heartbeat
    - ``dead``: >360s since last heartbeat
    """

    id: Optional[str] = None
    user_id: Optional[str] = None
    worker_id: str
    handlers: Optional[List[str]] = None
    last_heartbeat: Optional[datetime] = None
    heartbeat_status: Optional[str] = None
    seconds_since_heartbeat: Optional[int] = None
    api_key_id: Optional[str] = None
    created_at: Optional[datetime] = None
    model_config = {"extra": "allow"}


class WorkerList(BaseModel):
    """Typed accessor for ``client.workers.list()`` responses."""

    workers: List[Worker]
    total: Optional[int] = None
    model_config = {"extra": "allow"}
