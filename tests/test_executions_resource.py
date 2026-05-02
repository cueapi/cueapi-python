"""Tests for ExecutionsResource and ExecutionContext."""

import pytest
from unittest.mock import MagicMock

from cueapi.resources.executions import ExecutionsResource, ExecutionContext


class TestReportOutcome:
    def test_report_success(self):
        mock_client = MagicMock()
        mock_client._post.return_value = {"outcome_recorded": True}
        resource = ExecutionsResource(mock_client)

        result = resource.report_outcome("exec_123", success=True, result="done")

        mock_client._post.assert_called_once_with(
            "/v1/executions/exec_123/outcome",
            json={"success": True, "result": "done"},
        )

    def test_report_failure(self):
        mock_client = MagicMock()
        mock_client._post.return_value = {"outcome_recorded": True}
        resource = ExecutionsResource(mock_client)

        result = resource.report_outcome("exec_123", success=False, error="boom")

        mock_client._post.assert_called_once_with(
            "/v1/executions/exec_123/outcome",
            json={"success": False, "error": "boom"},
        )

    def test_report_with_evidence(self):
        mock_client = MagicMock()
        mock_client._post.return_value = {"outcome_recorded": True}
        resource = ExecutionsResource(mock_client)

        resource.report_outcome(
            "exec_123",
            success=True,
            external_id="tweet:123",
            result_url="https://twitter.com/user/123",
            result_type="tweet",
        )

        call_args = mock_client._post.call_args
        body = call_args.kwargs["json"]
        assert body["external_id"] == "tweet:123"
        assert body["result_type"] == "tweet"
        assert body["success"] is True


class TestContextManager:
    def test_clean_exit_reports_success(self):
        mock_client = MagicMock()
        mock_client._post.return_value = {"outcome_recorded": True}
        resource = ExecutionsResource(mock_client)

        with resource.handle("exec_123") as ctx:
            ctx.result = "processed 42 records"

        mock_client._post.assert_called_once()
        call_args = mock_client._post.call_args
        body = call_args.kwargs["json"]
        assert body["success"] is True
        assert "processed 42" in body.get("result", "")

    def test_exception_reports_failure(self):
        mock_client = MagicMock()
        mock_client._post.return_value = {"outcome_recorded": True}
        resource = ExecutionsResource(mock_client)

        with pytest.raises(ValueError):
            with resource.handle("exec_123") as ctx:
                raise ValueError("something broke")

        mock_client._post.assert_called_once()
        call_args = mock_client._post.call_args
        body = call_args.kwargs["json"]
        assert body["success"] is False
        assert "something broke" in body.get("error", "")

    def test_payload_passed_through(self):
        mock_client = MagicMock()
        mock_client._post.return_value = {"outcome_recorded": True}
        resource = ExecutionsResource(mock_client)

        with resource.handle("exec_123", payload={"task": "sync"}) as ctx:
            assert ctx.payload == {"task": "sync"}
            ctx.result = "ok"


class TestList:
    def test_list_basic(self):
        mock_client = MagicMock()
        mock_client._get.return_value = {"executions": [], "total": 0}
        resource = ExecutionsResource(mock_client)

        resource.list(cue_id="cue_123", limit=10)

        mock_client._get.assert_called_once()
        call_args = mock_client._get.call_args
        assert call_args.kwargs["params"]["cue_id"] == "cue_123"
        assert call_args.kwargs["params"]["limit"] == 10

    def test_list_defaults(self):
        mock_client = MagicMock()
        mock_client._get.return_value = {"executions": [], "total": 0}
        resource = ExecutionsResource(mock_client)

        resource.list()

        call_args = mock_client._get.call_args
        params = call_args.kwargs["params"]
        assert params["limit"] == 20
        assert params["offset"] == 0
        assert "cue_id" not in params


class TestGet:
    def test_get(self):
        mock_client = MagicMock()
        mock_client._get.return_value = {"id": "exec_123"}
        resource = ExecutionsResource(mock_client)

        resource.get("exec_123")

        mock_client._get.assert_called_once_with("/v1/executions/exec_123")


class TestHeartbeat:
    def test_heartbeat(self):
        mock_client = MagicMock()
        mock_client._post.return_value = {"acknowledged": True}
        resource = ExecutionsResource(mock_client)

        resource.heartbeat("exec_123")

        mock_client._post.assert_called_once_with(
            "/v1/executions/exec_123/heartbeat", json={},
        )


class TestVerification:
    def test_mark_verification_pending(self):
        mock_client = MagicMock()
        mock_client._post.return_value = {"outcome_state": "verification_pending"}
        resource = ExecutionsResource(mock_client)

        resource.mark_verification_pending("exec_123")

        mock_client._post.assert_called_once_with(
            "/v1/executions/exec_123/verification-pending", json={},
        )

    def test_mark_verified(self):
        mock_client = MagicMock()
        mock_client._post.return_value = {"outcome_state": "verified_success"}
        resource = ExecutionsResource(mock_client)

        resource.mark_verified("exec_123")

        mock_client._post.assert_called_once_with(
            "/v1/executions/exec_123/verify", json={},
        )


class TestListClaimable:
    # Filtering MUST be server-side via query params, not client-side after
    # fetch. Client-side filter hits the LIMIT 50 starvation bug fixed in the
    # 2026-04-25 prod incident (see cueapi-core app/routers/executions.py
    # docstring at line 122-131).

    def test_list_claimable_no_filters_sends_no_params(self):
        mock_client = MagicMock()
        mock_client._get.return_value = {"executions": []}
        resource = ExecutionsResource(mock_client)

        resource.list_claimable()

        mock_client._get.assert_called_once_with(
            "/v1/executions/claimable", params={},
        )

    def test_list_claimable_passes_task_as_query_param(self):
        mock_client = MagicMock()
        mock_client._get.return_value = {"executions": []}
        resource = ExecutionsResource(mock_client)

        resource.list_claimable(task="cowork-workspace")

        mock_client._get.assert_called_once_with(
            "/v1/executions/claimable",
            params={"task": "cowork-workspace"},
        )

    def test_list_claimable_passes_agent_as_query_param(self):
        mock_client = MagicMock()
        mock_client._get.return_value = {"executions": []}
        resource = ExecutionsResource(mock_client)

        resource.list_claimable(agent="writer-bot")

        mock_client._get.assert_called_once_with(
            "/v1/executions/claimable",
            params={"agent": "writer-bot"},
        )

    def test_list_claimable_passes_both_task_and_agent(self):
        mock_client = MagicMock()
        mock_client._get.return_value = {"executions": []}
        resource = ExecutionsResource(mock_client)

        resource.list_claimable(task="t", agent="a")

        mock_client._get.assert_called_once_with(
            "/v1/executions/claimable",
            params={"task": "t", "agent": "a"},
        )


class TestClaim:
    def test_claim_posts_to_specific_execution_with_worker_id_in_body(self):
        mock_client = MagicMock()
        mock_client._post.return_value = {
            "claimed": True,
            "execution_id": "exec_abc123",
            "lease_seconds": 900,
        }
        resource = ExecutionsResource(mock_client)

        result = resource.claim("exec_abc123", worker_id="cowork-workspace")

        mock_client._post.assert_called_once_with(
            "/v1/executions/exec_abc123/claim",
            json={"worker_id": "cowork-workspace"},
        )
        assert result["claimed"] is True


class TestClaimNext:
    # Two branches: with task and without. Without task is a single POST.
    # With task is a fan-out (list_claimable filtered, pick first, claim by ID)
    # because the server's POST /v1/executions/claim does not accept a task
    # filter today.

    def test_claim_next_without_task_sends_single_post(self):
        mock_client = MagicMock()
        mock_client._post.return_value = {
            "claimed": True,
            "execution_id": "exec_test",
            "lease_seconds": 900,
        }
        resource = ExecutionsResource(mock_client)

        resource.claim_next(worker_id="cowork-workspace")

        mock_client._post.assert_called_once_with(
            "/v1/executions/claim",
            json={"worker_id": "cowork-workspace"},
        )

    def test_claim_next_with_task_fans_out_to_list_then_claim(self):
        mock_client = MagicMock()
        mock_client._get.return_value = {
            "executions": [
                {"execution_id": "exec_first"},
                {"execution_id": "exec_second"},
            ],
        }
        mock_client._post.return_value = {
            "claimed": True,
            "execution_id": "exec_first",
            "lease_seconds": 900,
        }
        resource = ExecutionsResource(mock_client)

        result = resource.claim_next(
            worker_id="cowork-workspace", task="cowork-workspace"
        )

        mock_client._get.assert_called_once_with(
            "/v1/executions/claimable", params={"task": "cowork-workspace"},
        )
        mock_client._post.assert_called_once_with(
            "/v1/executions/exec_first/claim",
            json={"worker_id": "cowork-workspace"},
        )
        assert result["claimed"] is True

    def test_claim_next_with_task_and_empty_list_returns_no_claim(self):
        mock_client = MagicMock()
        mock_client._get.return_value = {"executions": []}
        resource = ExecutionsResource(mock_client)

        result = resource.claim_next(
            worker_id="cowork-workspace", task="no-such-task"
        )

        mock_client._post.assert_not_called()
        assert result == {
            "claimed": False,
            "reason": "no_executions_for_task",
            "task": "no-such-task",
        }
