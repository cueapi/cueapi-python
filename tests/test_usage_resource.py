"""Tests for UsageResource."""

from unittest.mock import MagicMock

from cueapi.resources.usage import UsageResource


class TestGet:
    def test_get_calls_get_usage(self):
        mock_client = MagicMock()
        mock_client._get.return_value = {
            "plan": {"name": "pro", "interval": "monthly"},
            "cues": {"active": 12, "limit": 100},
            "executions": {"used": 543, "limit": 5000},
            "rate_limit": {"limit": 200},
        }
        resource = UsageResource(mock_client)

        result = resource.get()

        mock_client._get.assert_called_once_with("/v1/usage")
        assert result["plan"]["name"] == "pro"
        assert result["cues"]["active"] == 12

    def test_get_returns_server_dict_unchanged(self):
        # Pin the no-transform behavior so a future refactor can't
        # silently start coercing the response into a typed object
        # without bumping the major version.
        mock_client = MagicMock()
        mock_client._get.return_value = {"unexpected_field": "value"}
        resource = UsageResource(mock_client)

        result = resource.get()
        assert result == {"unexpected_field": "value"}
