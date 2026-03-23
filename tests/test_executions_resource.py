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
