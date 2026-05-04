"""Message Pydantic model — typed accessor for messaging-primitive message responses.

Closes the Message portion of cueapi-python #24's `model_drift` manifest.
``MessagesResource`` methods currently return raw dicts; callers can opt
into typed accessors via ``Message.model_validate(client.messages.get(id))``
or ``MessageList.model_validate(client.agents.inbox(ref))``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FromAgentRef(BaseModel):
    """Inline agent reference rendered on incoming-message responses."""

    agent_id: Optional[str] = None
    slug: Optional[str] = None
    model_config = {"extra": "allow"}


class StateTransitionResponse(BaseModel):
    """Response shape for ``mark_read`` and ``ack`` endpoints."""

    delivery_state: str
    read_at: Optional[datetime] = None
    acked_at: Optional[datetime] = None
    model_config = {"extra": "allow"}


class Message(BaseModel):
    """Typed accessor for a messaging-primitive message (Phase 12.1.5).

    Mirrors the server's ``MessageResponse`` schema. Both inbox-fetched
    and sent-fetched messages use this shape; the ``from`` / ``to`` slots
    capture sender / recipient regardless of perspective.
    """

    id: str
    user_id: Optional[str] = None
    # Sender — populated on inbox responses; may be self on sent responses.
    # Pydantic treats `from` as a reserved keyword, but the server uses it
    # in the response. Use alias for clean access via .from_agent.
    from_agent: Optional[FromAgentRef] = Field(default=None, alias="from")
    to: Optional[str] = None
    body: Optional[str] = None
    subject: Optional[str] = None
    thread_id: Optional[str] = None
    reply_to: Optional[str] = None
    reply_to_agent: Optional[str] = None
    priority: Optional[int] = None
    expects_reply: Optional[bool] = None
    delivery_state: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None
    queued_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    acked_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"extra": "allow", "populate_by_name": True}


class MessageList(BaseModel):
    """Typed accessor for inbox / sent responses (lists of messages)."""

    messages: List[Message]
    total: Optional[int] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    model_config = {"extra": "allow"}
