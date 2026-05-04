"""Unit tests for the Cue Pydantic model — drift-against-hosted-API coverage.

These tests validate that the Cue model deserializes the full server
response shape, not just the subset the SDK had before the
2026-05-04 fix-up. Run against synthesized payloads that mirror what
the hosted ``app/schemas/cue.py CueResponse`` returns.
"""

from datetime import datetime, timezone

from cueapi.models.cue import (
    AlertConfig,
    Cue,
    CueList,
    DeliveryConfig,
    VerificationConfig,
)


def _base_cue_payload() -> dict:
    return {
        "id": "cue_test123",
        "name": "test-cue",
        "status": "active",
        "transport": "webhook",
        "schedule": {"type": "recurring", "cron": "0 9 * * *", "timezone": "UTC"},
        "callback": {"url": "https://example.com/webhook", "method": "POST"},
        "payload": {},
        "retry": {"max_attempts": 3, "backoff_minutes": [1, 5, 15]},
        "next_run": None,
        "last_run": None,
        "run_count": 0,
        "fired_count": 0,
        "warning": None,
        "created_at": "2026-05-04T17:00:00Z",
        "updated_at": "2026-05-04T17:00:00Z",
    }


class TestNewFields:
    def test_old_response_still_parses(self):
        # Older server responses without the new fields must still
        # deserialize cleanly. Pinning so a future required-field
        # addition doesn't break SDK callers reading legacy data.
        cue = Cue.model_validate(_base_cue_payload())
        assert cue.delivery is None
        assert cue.alerts is None
        assert cue.catch_up is None
        assert cue.verification is None
        assert cue.on_success_fire is None
        assert cue.require_payload_override is False
        assert cue.required_payload_keys is None
        assert cue.stats is None

    def test_delivery_config_parses(self):
        payload = _base_cue_payload()
        payload["delivery"] = {"timeout_seconds": 60, "outcome_deadline_seconds": 600}
        cue = Cue.model_validate(payload)
        assert isinstance(cue.delivery, DeliveryConfig)
        assert cue.delivery.timeout_seconds == 60
        assert cue.delivery.outcome_deadline_seconds == 600

    def test_alerts_config_forward_compat(self):
        # AlertConfig has extra="allow" so server can grow the object
        # without the SDK breaking. Pin the forward-compat behavior.
        payload = _base_cue_payload()
        payload["alerts"] = {
            "channels": ["email", "slack"],
            "future_field_we_dont_know_about_yet": "value",
        }
        cue = Cue.model_validate(payload)
        assert isinstance(cue.alerts, AlertConfig)
        assert cue.alerts.model_extra["channels"] == ["email", "slack"]
        assert cue.alerts.model_extra["future_field_we_dont_know_about_yet"] == "value"

    def test_catch_up_passthrough(self):
        for v in ("run_once_if_missed", "skip_missed", "replay_all"):
            payload = _base_cue_payload()
            payload["catch_up"] = v
            cue = Cue.model_validate(payload)
            assert cue.catch_up == v

    def test_verification_config_with_assertions(self):
        payload = _base_cue_payload()
        payload["verification"] = {
            "mode": "evidence_required",
            "required_assertions": ["external_id", "result_url"],
        }
        cue = Cue.model_validate(payload)
        assert isinstance(cue.verification, VerificationConfig)
        assert cue.verification.mode == "evidence_required"
        assert cue.verification.required_assertions == ["external_id", "result_url"]

    def test_verification_config_forward_compat(self):
        payload = _base_cue_payload()
        payload["verification"] = {
            "mode": "manual",
            "future_assertion_subkey": {"nested": True},
        }
        cue = Cue.model_validate(payload)
        assert cue.verification.mode == "manual"
        assert cue.verification.model_extra["future_assertion_subkey"] == {"nested": True}

    def test_on_success_fire(self):
        payload = _base_cue_payload()
        payload["on_success_fire"] = "cue_chained123"
        cue = Cue.model_validate(payload)
        assert cue.on_success_fire == "cue_chained123"

    def test_require_payload_override_explicitly_true(self):
        payload = _base_cue_payload()
        payload["require_payload_override"] = True
        payload["required_payload_keys"] = ["task", "message"]
        cue = Cue.model_validate(payload)
        assert cue.require_payload_override is True
        assert cue.required_payload_keys == ["task", "message"]

    def test_stats_blob(self):
        # CueDetailResponse-only field. Pin that the SDK accepts the
        # blob shape the server returns, opaquely (the keys evolve
        # server-side and we don't want to lock them).
        payload = _base_cue_payload()
        payload["stats"] = {
            "success_rate_7d": 0.94,
            "miss_rate_7d": 0.02,
            "total_executions_7d": 156,
        }
        cue = Cue.model_validate(payload)
        assert cue.stats == {
            "success_rate_7d": 0.94,
            "miss_rate_7d": 0.02,
            "total_executions_7d": 156,
        }


class TestRoundTrip:
    def test_full_response_roundtrip(self):
        # Comprehensive: every new field set, ensure the model accepts
        # the union shape and re-serializes to a dict that contains all
        # the field names the server expects to see in a write-side
        # request (when the SDK eventually grows builder-style helpers
        # that send these fields back to the server).
        payload = _base_cue_payload()
        payload.update({
            "delivery": {"timeout_seconds": 90, "outcome_deadline_seconds": 900},
            "alerts": {"channels": ["email"]},
            "catch_up": "skip_missed",
            "verification": {
                "mode": "evidence_required",
                "required_assertions": ["external_id"],
            },
            "on_success_fire": "cue_next",
            "require_payload_override": True,
            "required_payload_keys": ["task"],
            "stats": {"success_rate_7d": 1.0},
        })
        cue = Cue.model_validate(payload)

        # All fields present in dict roundtrip.
        d = cue.model_dump()
        assert d["delivery"]["timeout_seconds"] == 90
        assert d["catch_up"] == "skip_missed"
        assert d["on_success_fire"] == "cue_next"
        assert d["require_payload_override"] is True
        assert d["required_payload_keys"] == ["task"]


class TestCueList:
    def test_list_with_new_fields_in_each_cue(self):
        list_payload = {
            "cues": [
                {**_base_cue_payload(), "id": "cue_1", "require_payload_override": True},
                {**_base_cue_payload(), "id": "cue_2", "catch_up": "replay_all"},
            ],
            "total": 2,
            "limit": 50,
            "offset": 0,
        }
        cl = CueList.model_validate(list_payload)
        assert len(cl.cues) == 2
        assert cl.cues[0].require_payload_override is True
        assert cl.cues[1].catch_up == "replay_all"
