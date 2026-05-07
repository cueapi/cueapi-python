"""Tests for AgentsResource."""

import pytest
from unittest.mock import MagicMock

from cueapi.resources.agents import AgentsResource


class TestCreate:
    def test_minimal_only_display_name(self):
        mock_client = MagicMock()
        mock_client._post.return_value = {
            "id": "agt_x", "slug": "team-comm", "display_name": "Team Comm",
            "status": "online",
        }
        r = AgentsResource(mock_client)

        r.create(display_name="Team Comm")

        mock_client._post.assert_called_once_with(
            "/v1/agents",
            json={"display_name": "Team Comm"},
        )

    def test_with_all_optionals(self):
        mock_client = MagicMock()
        mock_client._post.return_value = {
            "id": "agt_x", "slug": "team-comm", "display_name": "Team Comm",
            "status": "online", "webhook_url": "https://x.example",
            "webhook_secret": "wsec_secretvalue",
        }
        r = AgentsResource(mock_client)

        r.create(
            display_name="Team Comm",
            slug="team-comm",
            webhook_url="https://x.example/webhook",
            metadata={"team": "platform"},
        )

        mock_client._post.assert_called_once_with(
            "/v1/agents",
            json={
                "display_name": "Team Comm",
                "slug": "team-comm",
                "webhook_url": "https://x.example/webhook",
                "metadata": {"team": "platform"},
            },
        )


class TestList:
    def test_defaults_omit_filters(self):
        mock_client = MagicMock()
        mock_client._get.return_value = {"agents": [], "total": 0}
        r = AgentsResource(mock_client)

        r.list()

        params = mock_client._get.call_args.kwargs["params"]
        assert params["limit"] == 50
        assert params["offset"] == 0
        assert "status" not in params
        assert "include_deleted" not in params

    def test_include_deleted_only_sent_when_true(self):
        # Same omit-when-default pattern as `executions list --has-evidence`
        # in the CLI. Pinned so a refactor can't silently start sending
        # `include_deleted=false` (which is no-op server-side but adds noise).
        mock_client = MagicMock()
        mock_client._get.return_value = {"agents": [], "total": 0}
        r = AgentsResource(mock_client)

        r.list(include_deleted=True)
        assert mock_client._get.call_args.kwargs["params"]["include_deleted"] == "true"

        # Reset, run with default — must omit.
        mock_client.reset_mock()
        r.list()
        assert "include_deleted" not in mock_client._get.call_args.kwargs["params"]

    def test_status_filter_passed(self):
        mock_client = MagicMock()
        mock_client._get.return_value = {"agents": [], "total": 0}
        r = AgentsResource(mock_client)

        r.list(status="online")

        assert mock_client._get.call_args.kwargs["params"]["status"] == "online"


class TestGet:
    def test_get_basic(self):
        mock_client = MagicMock()
        mock_client._get.return_value = {"id": "agt_x"}
        r = AgentsResource(mock_client)

        r.get("agt_x")

        mock_client._get.assert_called_once_with("/v1/agents/agt_x", params={})

    def test_get_with_include_deleted(self):
        mock_client = MagicMock()
        mock_client._get.return_value = {"id": "agt_x"}
        r = AgentsResource(mock_client)

        r.get("agt_x", include_deleted=True)

        mock_client._get.assert_called_once_with(
            "/v1/agents/agt_x", params={"include_deleted": "true"}
        )


class TestUpdate:
    def test_partial_body(self):
        mock_client = MagicMock()
        mock_client._patch.return_value = {"id": "agt_x"}
        r = AgentsResource(mock_client)

        r.update("agt_x", status="away")

        mock_client._patch.assert_called_once_with(
            "/v1/agents/agt_x", json={"status": "away"}
        )

    def test_clear_webhook_url_sends_explicit_null(self):
        # Mirror of cueapi-cli #28's --clear-webhook-url pin. Server uses
        # model_fields_set to disambiguate "field omitted = no change"
        # vs "field explicitly null = clear", so the SDK MUST send None
        # (literal JSON null) rather than omit the key.
        mock_client = MagicMock()
        mock_client._patch.return_value = {"id": "agt_x"}
        r = AgentsResource(mock_client)

        r.update("agt_x", clear_webhook_url=True)

        sent_body = mock_client._patch.call_args.kwargs["json"]
        assert "webhook_url" in sent_body
        assert sent_body["webhook_url"] is None

    def test_webhook_url_and_clear_mutually_exclusive(self):
        mock_client = MagicMock()
        r = AgentsResource(mock_client)

        with pytest.raises(ValueError, match="mutually exclusive"):
            r.update("agt_x", webhook_url="https://x.example", clear_webhook_url=True)


class TestDelete:
    def test_delete(self):
        mock_client = MagicMock()
        mock_client._delete.return_value = None
        r = AgentsResource(mock_client)

        result = r.delete("agt_x")

        mock_client._delete.assert_called_once_with("/v1/agents/agt_x")
        assert result is None


class TestWebhookSecret:
    def test_get(self):
        mock_client = MagicMock()
        mock_client._get.return_value = {"webhook_secret": "wsec_revealed"}
        r = AgentsResource(mock_client)

        r.webhook_secret_get("agt_x")

        mock_client._get.assert_called_once_with("/v1/agents/agt_x/webhook-secret")

    def test_regenerate_sends_destructive_header(self):
        # Server requires X-Confirm-Destructive: true for this op. Pin
        # the header so a refactor can't drop it (which would 400).
        mock_client = MagicMock()
        mock_client._post.return_value = {"webhook_secret": "wsec_new"}
        r = AgentsResource(mock_client)

        r.webhook_secret_regenerate("agt_x")

        mock_client._post.assert_called_once_with(
            "/v1/agents/agt_x/webhook-secret/regenerate",
            json={},
            headers={"X-Confirm-Destructive": "true"},
        )


class TestInbox:
    def test_inbox_basic(self):
        mock_client = MagicMock()
        mock_client._get.return_value = {"messages": [], "total": 0}
        r = AgentsResource(mock_client)

        r.inbox("agt_x")

        params = mock_client._get.call_args.kwargs["params"]
        assert params == {"limit": 50, "offset": 0}

    def test_inbox_with_state_filter(self):
        mock_client = MagicMock()
        mock_client._get.return_value = {"messages": [], "total": 0}
        r = AgentsResource(mock_client)

        r.inbox("agt_x", state="queued")

        assert mock_client._get.call_args.kwargs["params"]["state"] == "queued"


class TestSent:
    def test_sent_basic(self):
        mock_client = MagicMock()
        mock_client._get.return_value = {"messages": [], "total": 0}
        r = AgentsResource(mock_client)

        r.sent("agt_x")

        mock_client._get.assert_called_once_with(
            "/v1/agents/agt_x/sent",
            params={"limit": 50, "offset": 0},
        )


class TestRoster:
    """Agent directory roster — cueapi #630 parity."""

    def test_roster_no_etag(self):
        mock_client = MagicMock()
        mock_client._get.return_value = {"agents": [], "etag": "abc"}
        r = AgentsResource(mock_client)

        r.roster()

        # No If-None-Match header when if_none_match is None
        mock_client._get.assert_called_once_with("/v1/agents/roster")

    def test_roster_with_if_none_match(self):
        """If-None-Match flows as a header (not a query param)."""
        mock_client = MagicMock()
        mock_client._get.return_value = {"agents": [], "etag": "v2"}
        r = AgentsResource(mock_client)

        r.roster(if_none_match="W/\"abc\"")

        mock_client._get.assert_called_once_with(
            "/v1/agents/roster",
            headers={"If-None-Match": 'W/"abc"'},
        )


class TestPresence:
    """Cheap-poll presence — cueapi #662 parity."""

    def test_presence_by_id(self):
        mock_client = MagicMock()
        mock_client._get.return_value = {
            "online": True,
            "derived_status": "active",
            "bucketed_seen": "now",
        }
        r = AgentsResource(mock_client)

        r.presence("agt_abcdef123456")

        mock_client._get.assert_called_once_with("/v1/agents/agt_abcdef123456/presence")

    def test_presence_by_slug_form(self):
        mock_client = MagicMock()
        mock_client._get.return_value = {"online": False}
        r = AgentsResource(mock_client)

        r.presence("foo@me")

        mock_client._get.assert_called_once_with("/v1/agents/foo@me/presence")
