"""Tests for CuePayload builder."""

from cueapi.payload import CuePayload


class TestPayloadBuilder:
    def test_basic(self):
        payload = CuePayload().task("morning-brief").build()
        assert payload == {"task": "morning-brief"}

    def test_full(self):
        payload = (
            CuePayload()
            .task("morning-brief")
            .kind("content_generation")
            .instruction("Generate the morning briefing")
            .context_ref("mem_abc123")
            .context_mode("isolated")
            .agent("socrates")
            .build()
        )
        assert payload["task"] == "morning-brief"
        assert payload["kind"] == "content_generation"
        assert payload["agent"] == "socrates"
        assert payload["context_mode"] == "isolated"
        assert payload["instruction"] == "Generate the morning briefing"
        assert payload["context_ref"] == "mem_abc123"
        assert len(payload) == 6

    def test_extra_field(self):
        payload = CuePayload().task("sync").extra("region", "us-east-1").build()
        assert payload["region"] == "us-east-1"

    def test_chaining(self):
        p = CuePayload()
        result = p.task("test")
        assert result is p  # verify fluent chaining returns self

    def test_empty_build(self):
        payload = CuePayload().build()
        assert payload == {}

    def test_build_returns_copy(self):
        p = CuePayload().task("test")
        d1 = p.build()
        d2 = p.build()
        assert d1 == d2
        assert d1 is not d2  # separate dict instances
