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
