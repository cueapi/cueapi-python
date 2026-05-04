"""Tests for WorkersResource."""

from unittest.mock import MagicMock

from cueapi.resources.workers import WorkersResource


class TestList:
    def test_list_calls_get_workers(self):
        mock_client = MagicMock()
        mock_client._get.return_value = {
            "workers": [
                {
                    "worker_id": "worker-1",
                    "handlers": ["task-a"],
                    "last_heartbeat": "2026-05-04T17:30:00Z",
                    "heartbeat_status": "online",
                    "seconds_since_heartbeat": 5,
                }
            ],
            "total": 1,
        }
        resource = WorkersResource(mock_client)

        result = resource.list()

        mock_client._get.assert_called_once_with("/v1/workers")
        assert result["total"] == 1
        assert result["workers"][0]["worker_id"] == "worker-1"

    def test_list_passes_no_params(self):
        # Endpoint accepts no query params; SDK MUST NOT silently start
        # passing params (would couple to a future server-side change).
        # Pinning the bare-call shape.
        mock_client = MagicMock()
        mock_client._get.return_value = {"workers": [], "total": 0}
        resource = WorkersResource(mock_client)

        resource.list()

        mock_client._get.assert_called_once_with("/v1/workers")
        # No params kwarg.
        assert "params" not in mock_client._get.call_args.kwargs


class TestDelete:
    def test_delete_calls_delete_workers_id(self):
        mock_client = MagicMock()
        mock_client._delete.return_value = None  # 204 -> None per client _request
        resource = WorkersResource(mock_client)

        result = resource.delete("worker-1")

        mock_client._delete.assert_called_once_with("/v1/workers/worker-1")
        assert result is None
