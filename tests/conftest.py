"""Shared test fixtures."""

import os

import pytest

from cueapi import CueAPI

STAGING_URL = "https://api-staging-e962.up.railway.app"
STAGING_KEY = os.environ.get("CUEAPI_TEST_KEY", "cue_sk_f22857d8225de1b862995e2baa2ccdd8")


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
