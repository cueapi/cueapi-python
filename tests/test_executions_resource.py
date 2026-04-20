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

    def test_report_with_result_ref(self):
        # result_ref was added in 0.1.4 (PR #20); confirm it reaches the body.
        mock_client = MagicMock()
        resource = ExecutionsResource(mock_client)

        resource.report_outcome(
            "exec_123",
            success=True,
            result_ref="batch-id:7842",
        )

        body = mock_client._post.call_args.kwargs["json"]
        assert body["result_ref"] == "batch-id:7842"
        assert body["success"] is True

    def test_report_with_summary(self):
        mock_client = MagicMock()
        resource = ExecutionsResource(mock_client)

        resource.report_outcome(
            "exec_123",
            success=True,
            summary="Generated 47 qualified leads",
        )

        body = mock_client._post.call_args.kwargs["json"]
        assert body["summary"] == "Generated 47 qualified leads"

    def test_report_with_artifacts(self):
        mock_client = MagicMock()
        resource = ExecutionsResource(mock_client)

        artifacts = [
            {"name": "leads.csv", "url": "https://storage/leads.csv"},
            {"name": "report.pdf", "url": "https://storage/report.pdf"},
        ]
        resource.report_outcome(
            "exec_123",
            success=True,
            artifacts=artifacts,
        )

        body = mock_client._post.call_args.kwargs["json"]
        assert body["artifacts"] == artifacts

    def test_report_with_metadata(self):
        mock_client = MagicMock()
        resource = ExecutionsResource(mock_client)

        resource.report_outcome(
            "exec_123",
            success=True,
            metadata={"agent": "lead-finder-v3", "duration_ms": 1420},
        )

        body = mock_client._post.call_args.kwargs["json"]
        assert body["metadata"] == {"agent": "lead-finder-v3", "duration_ms": 1420}

    def test_report_with_all_evidence_fields(self):
        # Single request that exercises every optional kwarg the API
        # currently accepts. Guards against a future refactor silently
        # dropping one of them.
        mock_client = MagicMock()
        resource = ExecutionsResource(mock_client)

        resource.report_outcome(
            "exec_123",
            success=True,
            result="ok",
            metadata={"foo": "bar"},
            external_id="ext-1",
            result_url="https://example.com/1",
            result_ref="ref-1",
            result_type="report",
            summary="done",
            artifacts=[{"name": "a.json", "url": "https://example.com/a"}],
        )

        body = mock_client._post.call_args.kwargs["json"]
        assert body == {
            "success": True,
            "result": "ok",
            "metadata": {"foo": "bar"},
            "external_id": "ext-1",
            "result_url": "https://example.com/1",
            "result_ref": "ref-1",
            "result_type": "report",
            "summary": "done",
            "artifacts": [{"name": "a.json", "url": "https://example.com/a"}],
        }

    def test_report_omits_none_kwargs(self):
        # Optional kwargs left at their None default must NOT appear
        # in the POST body. Important because the server distinguishes
        # "field not provided" from "field explicitly set to null"
        # for evidence merging semantics.
        mock_client = MagicMock()
        resource = ExecutionsResource(mock_client)

        resource.report_outcome("exec_123", success=True)

        body = mock_client._post.call_args.kwargs["json"]
        assert body == {"success": True}
        for key in (
            "result",
            "error",
            "metadata",
            "external_id",
            "result_url",
            "result_ref",
            "result_type",
            "summary",
            "artifacts",
        ):
            assert key not in body


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
