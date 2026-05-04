"""Usage resource — plan + cue + execution usage stats."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cueapi.client import CueAPI


class UsageResource:
    """Usage stats resource.

    Wraps ``GET /v1/usage`` for SDK callers who want plan + cue count +
    execution count + rate-limit info without parsing the broader
    ``/v1/auth/me`` response.
    """

    def __init__(self, client: "CueAPI") -> None:
        self._client = client

    def get(self) -> dict:
        """Get current usage stats.

        Returns:
            Dict with ``plan`` (name + interval + period_end),
            ``cues`` (active count + limit),
            ``executions`` (used this period + limit + outcomes summary),
            and ``rate_limit`` (requests/min limit).
        """
        return self._client._get("/v1/usage")
