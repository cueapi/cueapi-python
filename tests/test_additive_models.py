"""Tests for additive Pydantic models — Execution / Worker / Agent / Message.

These models close the remaining `model_drift` items in cueapi-python #24's
parity manifest. Resource methods still return raw dicts (additive only —
no breaking change to return types). Callers opt into typed accessors via
``Model.model_validate(dict)``.
"""

from cueapi import (
    Agent,
    AgentList,
    Execution,
    ExecutionList,
    Message,
    MessageList,
    StateTransitionResponse,
    Worker,
    WorkerList,
)


# --- Execution ---


class TestExecution:
    def test_minimal_response_parses(self):
        ex = Execution.model_validate({
            "id": "exec_abc",
            "cue_id": "cue_xyz",
            "scheduled_for": "2026-05-04T17:00:00Z",
            "status": "pending",
        })
        assert ex.id == "exec_abc"
        assert ex.status == "pending"
        assert ex.outcome is None
        assert ex.payload is None
        assert ex.attempts is None

    def test_with_payload_field_589(self):
        # Pin: hosted PR #589's `payload` field is surfaced.
        ex = Execution.model_validate({
            "id": "exec_abc",
            "cue_id": "cue_xyz",
            "scheduled_for": "2026-05-04T17:00:00Z",
            "status": "success",
            "payload": {"task": "demo", "key": "value"},
        })
        assert ex.payload == {"task": "demo", "key": "value"}

    def test_with_outcome_detail(self):
        ex = Execution.model_validate({
            "id": "exec_abc",
            "cue_id": "cue_xyz",
            "scheduled_for": "2026-05-04T17:00:00Z",
            "status": "success",
            "outcome": {
                "success": True,
                "result": "processed 42 records",
                "external_id": "tweet:123",
                "result_url": "https://twitter.com/user/123",
                "result_type": "tweet",
            },
            "outcome_state": "verified_success",
        })
        assert ex.outcome is not None
        assert ex.outcome.success is True
        assert ex.outcome.external_id == "tweet:123"
        assert ex.outcome_state == "verified_success"

    def test_forward_compat_extra_field(self):
        # Server may grow the response over time. Pin that unknown fields
        # are kept (extra="allow") rather than dropped.
        ex = Execution.model_validate({
            "id": "exec_abc",
            "cue_id": "cue_xyz",
            "scheduled_for": "2026-05-04T17:00:00Z",
            "status": "pending",
            "future_field_we_dont_know_about_yet": "value",
        })
        assert ex.model_extra["future_field_we_dont_know_about_yet"] == "value"


class TestExecutionList:
    def test_basic(self):
        el = ExecutionList.model_validate({
            "executions": [
                {
                    "id": "exec_1",
                    "cue_id": "cue_x",
                    "scheduled_for": "2026-05-04T17:00:00Z",
                    "status": "success",
                },
                {
                    "id": "exec_2",
                    "cue_id": "cue_x",
                    "scheduled_for": "2026-05-04T17:01:00Z",
                    "status": "pending",
                },
            ],
            "total": 2,
            "limit": 20,
            "offset": 0,
        })
        assert len(el.executions) == 2
        assert el.executions[0].id == "exec_1"
        assert el.executions[1].status == "pending"


# --- Worker ---


class TestWorker:
    def test_basic(self):
        w = Worker.model_validate({
            "worker_id": "worker-1",
            "handlers": ["task-a", "task-b"],
            "last_heartbeat": "2026-05-04T17:30:00Z",
            "heartbeat_status": "online",
            "seconds_since_heartbeat": 5,
        })
        assert w.worker_id == "worker-1"
        assert w.handlers == ["task-a", "task-b"]
        assert w.heartbeat_status == "online"

    def test_minimal(self):
        # Only worker_id is required; everything else is optional so older
        # server responses still parse.
        w = Worker.model_validate({"worker_id": "worker-1"})
        assert w.worker_id == "worker-1"
        assert w.handlers is None


class TestWorkerList:
    def test_basic(self):
        wl = WorkerList.model_validate({
            "workers": [
                {"worker_id": "worker-1", "heartbeat_status": "online"},
                {"worker_id": "worker-2", "heartbeat_status": "stale"},
            ],
            "total": 2,
        })
        assert len(wl.workers) == 2
        assert wl.workers[0].heartbeat_status == "online"


# --- Agent ---


class TestAgent:
    def test_minimal(self):
        a = Agent.model_validate({
            "id": "agt_x",
            "slug": "team-comm",
            "display_name": "Team Comm",
        })
        assert a.id == "agt_x"
        assert a.webhook_url is None
        assert a.webhook_secret is None
        assert a.metadata == {}

    def test_with_webhook_secret_one_time(self):
        # Server returns webhook_secret only on create + on regenerate.
        a = Agent.model_validate({
            "id": "agt_x",
            "slug": "team-comm",
            "display_name": "Team Comm",
            "webhook_url": "https://x.example/webhook",
            "webhook_secret": "wsec_one_time_value",
        })
        assert a.webhook_secret == "wsec_one_time_value"


class TestAgentList:
    def test_basic(self):
        al = AgentList.model_validate({
            "agents": [
                {"id": "agt_1", "slug": "a", "display_name": "A"},
                {"id": "agt_2", "slug": "b", "display_name": "B"},
            ],
            "total": 2,
            "limit": 50,
            "offset": 0,
        })
        assert len(al.agents) == 2


# --- Message ---


class TestMessage:
    def test_inbox_message_with_from_ref(self):
        m = Message.model_validate({
            "id": "msg_x",
            "from": {"agent_id": "agt_sender", "slug": "sender@x"},
            "to": "recipient@y",
            "body": "hello",
            "delivery_state": "delivered",
        })
        assert m.id == "msg_x"
        # Aliased: server's `from` → SDK's `from_agent`.
        assert m.from_agent is not None
        assert m.from_agent.slug == "sender@x"
        assert m.delivery_state == "delivered"

    def test_with_thread_and_reply(self):
        m = Message.model_validate({
            "id": "msg_reply",
            "subject": "re: hello",
            "body": "reply body",
            "thread_id": "thr_abc",
            "reply_to": "msg_original",
            "priority": 4,
            "expects_reply": True,
        })
        assert m.thread_id == "thr_abc"
        assert m.reply_to == "msg_original"
        assert m.priority == 4
        assert m.expects_reply is True


class TestMessageList:
    def test_basic(self):
        ml = MessageList.model_validate({
            "messages": [
                {"id": "msg_1", "delivery_state": "queued"},
                {"id": "msg_2", "delivery_state": "delivered"},
            ],
            "total": 2,
        })
        assert len(ml.messages) == 2


class TestStateTransitionResponse:
    def test_read(self):
        s = StateTransitionResponse.model_validate({
            "delivery_state": "read",
            "read_at": "2026-05-04T17:00:00Z",
        })
        assert s.delivery_state == "read"
        assert s.acked_at is None

    def test_ack(self):
        s = StateTransitionResponse.model_validate({
            "delivery_state": "acked",
            "acked_at": "2026-05-04T17:01:00Z",
        })
        assert s.delivery_state == "acked"


def test_all_models_exported_from_top_level():
    # Pin: every new model is importable from `cueapi` directly so callers
    # don't have to know the internal path.
    from pydantic import BaseModel
    from cueapi import (
        Agent, AgentList, Execution, ExecutionList, FromAgentRef,
        Message, MessageList, OutcomeDetail, StateTransitionResponse,
        Worker, WorkerList,
    )
    for cls in (Agent, AgentList, Execution, ExecutionList, FromAgentRef,
                Message, MessageList, OutcomeDetail, StateTransitionResponse,
                Worker, WorkerList):
        assert issubclass(cls, BaseModel), f"{cls.__name__} not a BaseModel"
