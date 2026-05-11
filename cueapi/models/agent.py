"""Agent Pydantic model — typed accessor for messaging-primitive agent responses.

Closes the Agent portion of cueapi-python #24's `model_drift` manifest.
``AgentsResource`` methods currently return raw dicts; callers can opt
into typed accessors via ``Agent.model_validate(client.agents.get(ref))``
or ``AgentList.model_validate(client.agents.list())``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class Agent(BaseModel):
    """Typed accessor for a messaging-primitive agent (Phase 12.1.5).

    ``webhook_secret`` is populated only on the response from
    ``client.agents.create()`` (when ``webhook_url`` was supplied) and
    from ``client.agents.webhook_secret_regenerate()``. Subsequent reads
    omit the secret.
    """

    id: str
    user_id: Optional[str] = None
    api_key_id: Optional[str] = None
    slug: str
    display_name: str
    webhook_url: Optional[str] = None
    # One-time on create + on regenerate; None on subsequent reads.
    webhook_secret: Optional[str] = None
    metadata: Dict[str, Any] = {}
    status: Optional[str] = None  # online / offline / away
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"extra": "allow"}


class AgentList(BaseModel):
    """Typed accessor for ``client.agents.list()`` responses."""

    agents: List[Agent]
    total: int
    limit: int
    offset: int
    model_config = {"extra": "allow"}
