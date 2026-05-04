"""Unit tests for CuesResource methods that don't fit the staging-integration pattern."""

from unittest.mock import MagicMock

from cueapi.resources.cues import CuesResource


class TestFire:
    def test_fire_no_payload_override(self):
        mock_client = MagicMock()
        mock_client._post.return_value = {"id": "exec_test", "status": "queued"}
        resource = CuesResource(mock_client)

        result = resource.fire("cue_abc123")

        mock_client._post.assert_called_once_with("/v1/cues/cue_abc123/fire", json={})
        assert result["id"] == "exec_test"

    def test_fire_with_payload_override_only(self):
        mock_client = MagicMock()
        mock_client._post.return_value = {"id": "exec_test"}
        resource = CuesResource(mock_client)

        payload = {"task": "downstream", "scope": "single-row"}
        resource.fire("cue_abc123", payload_override=payload)

        mock_client._post.assert_called_once_with(
            "/v1/cues/cue_abc123/fire",
            json={"payload_override": payload},
        )

    def test_fire_with_payload_override_and_merge_strategy(self):
        mock_client = MagicMock()
        mock_client._post.return_value = {"id": "exec_test"}
        resource = CuesResource(mock_client)

        payload = {"run_id": "ad-hoc-001"}
        resource.fire("cue_abc123", payload_override=payload, merge_strategy="replace")

        mock_client._post.assert_called_once_with(
            "/v1/cues/cue_abc123/fire",
            json={"payload_override": payload, "merge_strategy": "replace"},
        )

    def test_fire_omits_merge_strategy_when_not_passed(self):
        # When the caller omits merge_strategy, the wrapper must NOT send a
        # client-side default. The server's Pydantic default of "merge"
        # applies. This pins the contract so a future refactor can't silently
        # start sending a strategy that overrides the server's choice.
        mock_client = MagicMock()
        mock_client._post.return_value = {"id": "exec_test"}
        resource = CuesResource(mock_client)

        resource.fire("cue_abc123", payload_override={"k": "v"})

        sent_body = mock_client._post.call_args.kwargs["json"]
        assert "merge_strategy" not in sent_body

    def test_fire_with_send_at(self):
        # Hosted PR #618: per-fire scheduling. send_at as ISO string lands
        # in the body unchanged.
        mock_client = MagicMock()
        mock_client._post.return_value = {
            "id": "exec_test",
            "scheduled_for": "2026-05-04T20:00:00Z",
        }
        resource = CuesResource(mock_client)

        resource.fire("cue_abc123", send_at="2026-05-04T20:00:00Z")

        mock_client._post.assert_called_once_with(
            "/v1/cues/cue_abc123/fire",
            json={"send_at": "2026-05-04T20:00:00Z"},
        )

    def test_fire_omits_send_at_when_not_passed(self):
        # Pin: when send_at is None (default), the body must not include the
        # key. Sending null adds noise to the request and may interact poorly
        # with future Pydantic schemas.
        mock_client = MagicMock()
        mock_client._post.return_value = {"id": "exec_test"}
        resource = CuesResource(mock_client)

        resource.fire("cue_abc123")

        sent_body = mock_client._post.call_args.kwargs["json"]
        assert "send_at" not in sent_body

    def test_fire_combines_send_at_with_payload_override(self):
        mock_client = MagicMock()
        mock_client._post.return_value = {"id": "exec_test"}
        resource = CuesResource(mock_client)

        resource.fire(
            "cue_abc123",
            payload_override={"task": "demo"},
            merge_strategy="replace",
            send_at="2026-05-04T22:00:00Z",
        )

        mock_client._post.assert_called_once_with(
            "/v1/cues/cue_abc123/fire",
            json={
                "payload_override": {"task": "demo"},
                "merge_strategy": "replace",
                "send_at": "2026-05-04T22:00:00Z",
            },
        )
