"""CueAPI Python SDK — scheduling infrastructure for agents."""

from cueapi.client import CueAPI
from cueapi.exceptions import (
    AuthenticationError,
    CueAPIError,
    CueAPIServerError,
    CueLimitExceededError,
    CueNotFoundError,
    InvalidScheduleError,
    RateLimitError,
)
from cueapi.payload import CuePayload
from cueapi.resources.executions import ExecutionsResource
from cueapi.webhook import verify_webhook

__version__ = "0.1.0"

__all__ = [
    "CueAPI",
    "CuePayload",
    "ExecutionsResource",
    "verify_webhook",
    "CueAPIError",
    "AuthenticationError",
    "RateLimitError",
    "CueNotFoundError",
    "CueLimitExceededError",
    "InvalidScheduleError",
    "CueAPIServerError",
]
