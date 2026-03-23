"""CuePayload builder — standard agent scheduling payloads."""

from __future__ import annotations


class CuePayload:
    """Builder for standard agent scheduling payloads.

    Usage::

        payload = CuePayload()
        payload.task("morning-brief").kind("content_generation").agent("socrates")
        client.cues.create(name="morning-brief", cron="0 9 * * *", payload=payload.build())
    """

    def __init__(self):
        self._data = {}

    def task(self, task_name: str) -> CuePayload:
        """Set the task name (used for worker routing via ?task= filter)."""
        self._data["task"] = task_name
        return self

    def kind(self, kind: str) -> CuePayload:
        """Set the task kind (e.g., 'content_generation', 'data_sync', 'agent_turn')."""
        self._data["kind"] = kind
        return self

    def instruction(self, text: str) -> CuePayload:
        """Set the instruction text for the agent."""
        self._data["instruction"] = text
        return self

    def context_ref(self, ref: str) -> CuePayload:
        """Set a reference to the context (e.g., memory block ID)."""
        self._data["context_ref"] = ref
        return self

    def context_mode(self, mode: str) -> CuePayload:
        """Set context mode: 'full', 'summary', 'ref_only'."""
        self._data["context_mode"] = mode
        return self

    def agent(self, agent_name: str) -> CuePayload:
        """Set the agent name (metadata only -- not enforced in routing)."""
        self._data["agent"] = agent_name
        return self

    def extra(self, key: str, value) -> CuePayload:
        """Set an arbitrary extra field."""
        self._data[key] = value
        return self

    def build(self) -> dict:
        """Return the payload as a dictionary."""
        return dict(self._data)
