"""Tests for version information."""

import importlib
from unittest import mock

import athena_client.version
from athena_client.version import __version__


def test_version_from_metadata() -> None:
    """Test that version is correctly retrieved from package metadata."""
    with mock.patch("importlib.metadata.version") as mock_version:
        mock_version.return_value = "1.2.3"
        # Force reload of version module to get mocked value

        importlib.reload(athena_client.version)
        assert athena_client.version.__version__ == "1.2.3"


def test_version_exists() -> None:
    """Test that version string exists and is non-empty."""
    assert isinstance(__version__, str)
    assert len(__version__) > 0
