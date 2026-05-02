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
from cueapi.resources.agents import AgentsResource
from cueapi.resources.executions import ExecutionsResource
from cueapi.resources.messages import MessagesResource
from cueapi.resources.usage import UsageResource
from cueapi.resources.workers import WorkersResource
from cueapi.webhook import verify_webhook

__version__ = "0.2.0"

__all__ = [
    "AgentsResource",
    "CueAPI",
    "CuePayload",
    "ExecutionsResource",
    "MessagesResource",
    "UsageResource",
    "WorkersResource",
    "verify_webhook",
    "CueAPIError",
    "AuthenticationError",
    "RateLimitError",
    "CueNotFoundError",
    "CueLimitExceededError",
    "InvalidScheduleError",
    "CueAPIServerError",
]
