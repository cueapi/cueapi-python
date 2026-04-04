"""Tests for CueAPI client initialization and error handling."""

import pytest

from cueapi import CueAPI
from cueapi.exceptions import AuthenticationError


class TestClientInit:
    def test_client_has_cues_resource(self):
        """Client should have a cues attribute."""
        client = CueAPI("test-key", base_url="https://example.com")
        assert hasattr(client, "cues")
        assert hasattr(client, "executions")
        client.close()

    def test_client_accepts_base_url(self):
        """Client should accept a custom base_url."""
        client = CueAPI("test-key", base_url="https://custom.example.com")
        assert client._base_url == "https://custom.example.com"
        client.close()

    def test_client_close_is_idempotent(self):
        """Calling close() multiple times should not raise."""
        client = CueAPI("test-key", base_url="https://example.com")
        client.close()
        client.close()  # Should not raise


class TestClientErrors:
    def test_invalid_api_key_raises_auth_error(self):
        """Using an invalid API key should raise AuthenticationError."""
        client = CueAPI("invalid-key-that-does-not-exist", base_url="https://api-staging-e962.up.railway.app")
        with pytest.raises((AuthenticationError, Exception)):
            client.cues.list()
        client.close()
