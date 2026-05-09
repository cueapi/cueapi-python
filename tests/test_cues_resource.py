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


class TestBulkDelete:
    def test_bulk_delete_happy_path(self):
        mock_client = MagicMock()
        mock_client._post.return_value = {
            "deleted": ["cue_abc", "cue_def"],
            "skipped": [],
        }
        resource = CuesResource(mock_client)

        result = resource.bulk_delete(["cue_abc", "cue_def"])

        mock_client._post.assert_called_once_with(
            "/v1/cues/bulk-delete",
            json={"ids": ["cue_abc", "cue_def"]},
            headers={"X-Confirm-Destructive": "true"},
        )
        assert result == {"deleted": ["cue_abc", "cue_def"], "skipped": []}

    def test_bulk_delete_with_skipped(self):
        mock_client = MagicMock()
        mock_client._post.return_value = {
            "deleted": ["cue_abc"],
            "skipped": ["cue_xyz"],
        }
        resource = CuesResource(mock_client)

        result = resource.bulk_delete(["cue_abc", "cue_xyz"])

        assert result["deleted"] == ["cue_abc"]
        assert result["skipped"] == ["cue_xyz"]

    def test_bulk_delete_sends_confirm_destructive_header(self):
        # Pin the X-Confirm-Destructive header — server requires it for
        # any bulk-destructive endpoint. If a future refactor drops this
        # header, the server returns 400 confirmation_required and the
        # SDK call silently fails.
        mock_client = MagicMock()
        mock_client._post.return_value = {"deleted": ["cue_a"], "skipped": []}
        resource = CuesResource(mock_client)

        resource.bulk_delete(["cue_a"])

        kwargs = mock_client._post.call_args.kwargs
        assert kwargs["headers"]["X-Confirm-Destructive"] == "true"

    def test_bulk_delete_empty_ids_raises(self):
        mock_client = MagicMock()
        resource = CuesResource(mock_client)

        import pytest

        with pytest.raises(ValueError, match="at least one cue ID"):
            resource.bulk_delete([])

        # Server NOT called — fail-fast at SDK layer.
        mock_client._post.assert_not_called()

    def test_bulk_delete_over_100_ids_raises(self):
        mock_client = MagicMock()
        resource = CuesResource(mock_client)

        import pytest

        ids = [f"cue_{i}" for i in range(101)]
        with pytest.raises(ValueError, match="Max 100"):
            resource.bulk_delete(ids)

        mock_client._post.assert_not_called()

    def test_bulk_delete_exactly_100_ids_ok(self):
        # Boundary — 100 IDs is allowed (server cap is inclusive).
        mock_client = MagicMock()
        mock_client._post.return_value = {
            "deleted": [f"cue_{i}" for i in range(100)],
            "skipped": [],
        }
        resource = CuesResource(mock_client)

        ids = [f"cue_{i}" for i in range(100)]
        result = resource.bulk_delete(ids)

        assert len(result["deleted"]) == 100

    def test_bulk_delete_accepts_iterable_not_just_list(self):
        # The method coerces the input to a list before sending. Verifies
        # tuple / generator inputs work without explicit conversion at
        # the call site.
        mock_client = MagicMock()
        mock_client._post.return_value = {"deleted": ["cue_a"], "skipped": []}
        resource = CuesResource(mock_client)

        resource.bulk_delete(("cue_a",))

        sent_body = mock_client._post.call_args.kwargs["json"]
        assert sent_body == {"ids": ["cue_a"]}
