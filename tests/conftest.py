"""Shared test fixtures."""

import os

import pytest

from cueapi import CueAPI

STAGING_URL = os.environ.get("CUEAPI_STAGING_URL", "https://api-staging.cueapi.ai")
STAGING_KEY = os.environ.get("CUEAPI_STAGING_API_KEY", "")


@pytest.fixture
def client():
    """Create a CueAPI client pointed at staging."""
    c = CueAPI(STAGING_KEY, base_url=STAGING_URL)
    yield c
    c.close()


@pytest.fixture
def cue(client):
    """Create a test cue and clean it up after."""
    created = client.cues.create(
        name="sdk-test-cue",
        cron="0 12 * * *",
        callback="https://example.com/webhook",
        payload={"test": True},
    )
    yield created
    try:
        client.cues.delete(created.id)
    except Exception:
        pass
