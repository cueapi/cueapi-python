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
from cueapi.models.agent import Agent, AgentList
from cueapi.models.cue import Cue, CueList
from cueapi.models.execution import Execution, ExecutionList, OutcomeDetail
from cueapi.models.message import (
    FromAgentRef,
    Message,
    MessageList,
    StateTransitionResponse,
)
from cueapi.models.worker import Worker, WorkerList
from cueapi.payload import CuePayload
from cueapi.resources.agents import AgentsResource
from cueapi.resources.executions import ExecutionsResource
from cueapi.resources.messages import MessagesResource
from cueapi.resources.usage import UsageResource
from cueapi.resources.workers import WorkersResource
from cueapi.webhook import verify_webhook

__version__ = "0.2.0"

__all__ = [
    "Agent",
    "AgentList",
    "AgentsResource",
    "Cue",
    "CueAPI",
    "CueList",
    "CuePayload",
    "Execution",
    "ExecutionList",
    "ExecutionsResource",
    "FromAgentRef",
    "Message",
    "MessageList",
    "MessagesResource",
    "OutcomeDetail",
    "StateTransitionResponse",
    "UsageResource",
    "Worker",
    "WorkerList",
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
