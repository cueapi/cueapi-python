"""CueAPI exception classes."""

from __future__ import annotations

from typing import Any, Dict, Optional


class CueAPIError(Exception):
    """Base exception for all CueAPI errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
        body: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.code = code
        self.body = body or {}
        super().__init__(message)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, status_code={self.status_code})"


class AuthenticationError(CueAPIError):
    """Raised on 401 — invalid or missing API key."""


class RateLimitError(CueAPIError):
    """Raised on 429 — rate limit exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        **kwargs: Any,
    ):
        self.retry_after = retry_after
        super().__init__(message, **kwargs)


class CueNotFoundError(CueAPIError):
    """Raised on 404 — cue not found."""


class CueLimitExceededError(CueAPIError):
    """Raised on 403 — cue limit exceeded for current plan."""


class InvalidScheduleError(CueAPIError):
    """Raised on 400 — invalid cron expression or schedule."""


class CueAPIServerError(CueAPIError):
    """Raised on 5xx — server error."""
