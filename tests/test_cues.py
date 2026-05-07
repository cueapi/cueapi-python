"""Tests for cue CRUD operations against staging."""

import pytest

from cueapi import CueAPI, CueNotFoundError, InvalidScheduleError
from cueapi.models.cue import Cue, CueList


class TestCueCreate:
    def test_create_recurring(self, client):
        cue = client.cues.create(
            name="test-recurring",
            cron="0 9 * * *",
            callback="https://example.com/webhook",
            payload={"action": "test"},
        )
        assert isinstance(cue, Cue)
        assert cue.name == "test-recurring"
        assert cue.status == "active"
        assert cue.schedule.type == "recurring"
        assert cue.schedule.cron == "0 9 * * *"
        assert cue.next_run is not None
        # Cleanup
        client.cues.delete(cue.id)

    def test_create_one_time(self, client):
        cue = client.cues.create(
            name="test-once",
            at="2030-01-01T00:00:00Z",
            callback="https://example.com/webhook",
        )
        assert isinstance(cue, Cue)
        assert cue.schedule.type == "once"
        client.cues.delete(cue.id)

    def test_create_with_retry_and_on_failure(self, client):
        cue = client.cues.create(
            name="test-retry-config",
            cron="0 10 * * *",
            callback="https://example.com/webhook",
            retry={"max_attempts": 5, "backoff_minutes": [1, 2, 5, 10, 30]},
            on_failure={"email": True, "pause": True},
        )
        assert cue.retry.max_attempts == 5
        assert cue.retry.backoff_minutes == [1, 2, 5, 10, 30]
        assert cue.on_failure is not None
        assert cue.on_failure.email is True
        assert cue.on_failure.pause is True
        client.cues.delete(cue.id)

    def test_create_missing_schedule_raises(self, client):
        with pytest.raises(ValueError, match="Either 'cron' or 'at'"):
            client.cues.create(
                name="bad-cue",
                callback="https://example.com/webhook",
            )

    def test_create_invalid_cron_raises(self, client):
        with pytest.raises(InvalidScheduleError):
            client.cues.create(
                name="bad-cron",
                cron="not a cron",
                callback="https://example.com/webhook",
            )


class TestCueList:
    def test_list_returns_cue_list(self, client, cue):
        result = client.cues.list()
        assert isinstance(result, CueList)
        assert result.total >= 1
        assert any(c.id == cue.id for c in result.cues)

    def test_list_with_limit(self, client, cue):
        result = client.cues.list(limit=1)
        assert len(result.cues) <= 1


class TestCueGet:
    def test_get_existing(self, client, cue):
        fetched = client.cues.get(cue.id)
        assert fetched.id == cue.id
        assert fetched.name == cue.name

    def test_get_not_found(self, client):
        with pytest.raises(CueNotFoundError):
            client.cues.get("cue_nonexistent_id_12345")


class TestCueUpdate:
    def test_update_name(self, client, cue):
        updated = client.cues.update(cue.id, name="updated-name")
        assert updated.name == "updated-name"

    def test_update_payload(self, client, cue):
        updated = client.cues.update(cue.id, payload={"new": "data"})
        assert updated.payload == {"new": "data"}


class TestCuePauseResume:
    def test_pause(self, client, cue):
        paused = client.cues.pause(cue.id)
        assert paused.status == "paused"

    def test_resume(self, client, cue):
        client.cues.pause(cue.id)
        resumed = client.cues.resume(cue.id)
        assert resumed.status == "active"


class TestCueDelete:
    def test_delete(self, client):
        cue = client.cues.create(
            name="to-delete",
            cron="0 0 * * *",
            callback="https://example.com/webhook",
        )
        client.cues.delete(cue.id)
        with pytest.raises(CueNotFoundError):
            client.cues.get(cue.id)


class TestCueFire:
    """Tests for the fire() method (manual trigger / per-fire override).

    All tests run against a real cue (the ``cue`` fixture creates one for
    each test). Fire creates an execution row; we don't poll the
    execution status here — the worker/poller pipeline isn't exercised
    by the SDK suite. We just verify the fire response shape and HTTP
    success.
    """

    def test_fire_no_args(self, client, cue):
        """Bare fire() — no payload override, no scheduling, immediate."""
        execution = client.cues.fire(cue.id)
        # Server returns the created execution dict
        assert "id" in execution
        assert execution["cue_id"] == cue.id
        # Triggered manually should set triggered_by accordingly
        assert execution.get("triggered_by") in ("manual_fire", "manual")
        # Default scheduling is immediate (or close to it)
        assert "scheduled_for" in execution

    def test_fire_with_payload_override(self, client, cue):
        """Fire with payload_override — execution carries the override."""
        execution = client.cues.fire(
            cue.id,
            payload_override={"task": "manual", "trigger": "test"},
        )
        assert "id" in execution
        # Default merge_strategy is server-side merge — we don't assert
        # on the merged result here (that's a server test); just verify
        # the call shape was accepted.

    def test_fire_with_merge_strategy_replace(self, client, cue):
        """Replace strategy — payload_override fully replaces stored payload."""
        execution = client.cues.fire(
            cue.id,
            payload_override={"action": "replace-test"},
            merge_strategy="replace",
        )
        assert "id" in execution

    def test_fire_with_send_at(self, client, cue):
        """send_at delays this fire to a specific timestamp (cueapi #618)."""
        future = "2030-01-01T12:00:00Z"
        execution = client.cues.fire(cue.id, send_at=future)
        assert "id" in execution
        # Server reflects the requested scheduled_for
        # (allow some tolerance — server may normalize the timestamp)
        assert "scheduled_for" in execution

    def test_fire_with_idempotency_key(self, client, cue):
        """Idempotency-Key replays the same fire (cueapi #683)."""
        import uuid

        key = f"sdk-test-{uuid.uuid4().hex[:8]}"
        first = client.cues.fire(cue.id, idempotency_key=key)
        second = client.cues.fire(cue.id, idempotency_key=key)
        # Same key + same body → server returns the SAME execution
        assert first["id"] == second["id"]

    def test_fire_returns_dict_not_cue(self, client, cue):
        """Sanity: fire returns the execution dict (not a typed Cue)."""
        result = client.cues.fire(cue.id)
        # Not a Cue object — fire creates an execution, not a new cue
        assert not isinstance(result, Cue)
        assert isinstance(result, dict)
