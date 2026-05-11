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


class BodyVerifyMismatchError(CueAPIError):
    """Raised when ``messages.send(auto_verify=True)`` detects that the
    body the server received differs from the body the caller sent.

    Phase 2 of body-verify defense-in-depth (Mike directive 2026-05-11).
    Caught when ``X-CueAPI-Verify-Echo: true`` request header is sent +
    the server echoes back the received body in the response. The most
    likely cause: caller-side shell expansion of ``$(...)`` / backticks /
    ``${VAR}`` in the body arg BEFORE Python received it (e.g., a bash
    invocation that assembled the body via double-quoted-string-with-
    metacharacters before passing as argv).

    Attributes:
        sent_body: The body the SDK sent in the POST request.
        received_body: The body the server reports having received.
        first_divergence_byte: Zero-based byte offset of the first
            differing position; useful for pinpointing single-char drift.
            ``-1`` when one body is a proper prefix of the other (length
            difference rather than content drift).
        message_id: The server-assigned message ID (server stored the
            mutated content; caller can inspect via ``messages.get(...)``
            if needed for diagnostic / recovery purposes).
    """

    def __init__(
        self,
        message: str,
        *,
        sent_body: str,
        received_body: str,
        first_divergence_byte: int,
        message_id: str,
        **kwargs: Any,
    ):
        self.sent_body = sent_body
        self.received_body = received_body
        self.first_divergence_byte = first_divergence_byte
        self.message_id = message_id
        super().__init__(message, **kwargs)

    def __repr__(self) -> str:
        return (
            f"BodyVerifyMismatchError(message_id={self.message_id!r}, "
            f"first_divergence_byte={self.first_divergence_byte}, "
            f"sent_len={len(self.sent_body)}, "
            f"received_len={len(self.received_body)})"
        )


def first_divergence_byte(a: str, b: str) -> int:
    """Return the byte index of the first differing position between
    ``a`` and ``b``. Returns ``-1`` when ``a == b`` OR when one is a
    proper prefix of the other (length differs but the shorter is a
    clean prefix); the caller should distinguish length-mismatch from
    content-divergence by comparing ``len(a) == len(b)``.

    Pure function; no SDK dependency. Used by
    ``BodyVerifyMismatchError`` for diagnostic output + can be re-used
    cross-SDK (cueapi-cli, cueapi-action).
    """
    common_len = min(len(a), len(b))
    for i in range(common_len):
        if a[i] != b[i]:
            return i
    # Equal up to common_len. Either fully equal or one is a prefix of
    # the other. -1 signals the caller to check length-mismatch.
    return -1
