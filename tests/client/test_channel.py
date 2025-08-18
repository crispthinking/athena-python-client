"""Tests for gRPC channel creation utilities."""

from unittest import mock

import pytest
from grpc.aio import Channel

from athena_client.client.channel import create_channel
from athena_client.client.exceptions import InvalidAuthError, InvalidHostError


def test_create_channel() -> None:
    """Test channel creation with authentication token."""
    test_host = "test-host:50051"
    test_token = "test-token"  # noqa: S105 - Not a real token, just a test value

    # Mock the credentials and channel creation
    mock_credentials = mock.Mock()
    mock_channel = mock.Mock(spec=Channel)

    with (
        mock.patch("grpc.ssl_channel_credentials") as mock_ssl_creds,
        mock.patch("grpc.metadata_call_credentials") as mock_token_creds,
        mock.patch(
            "grpc.composite_channel_credentials"
        ) as mock_composite_creds,
        mock.patch("grpc.aio.secure_channel") as mock_secure_channel,
    ):
        # Set up mocks
        mock_ssl_creds.return_value = mock.Mock()
        mock_token_creds.return_value = mock.Mock()
        mock_composite_creds.return_value = mock_credentials
        mock_secure_channel.return_value = mock_channel

        # Create channel
        channel = create_channel(test_host, test_token)

        # Verify channel creation
        assert channel == mock_channel

        # Verify credentials were created correctly
        mock_ssl_creds.assert_called_once()
        mock_token_creds.assert_called_once_with(mock.ANY)
        mock_composite_creds.assert_called_once_with(
            mock_ssl_creds.return_value, mock_token_creds.return_value
        )
        mock_secure_channel.assert_called_once_with(test_host, mock_credentials)


def test_create_channel_with_invalid_host() -> None:
    """Test channel creation with invalid host raises error."""
    test_host = ""  # Invalid host
    test_token = "test-token"  # noqa: S105 - Not a real token, just a test value

    with pytest.raises(InvalidHostError, match="host cannot be empty"):
        create_channel(test_host, test_token)


def test_create_channel_with_empty_token() -> None:
    """Test channel creation with empty auth token raises error."""
    test_host = "test-host:50051"
    test_token = ""  # Empty token

    with pytest.raises(InvalidAuthError, match="auth_token cannot be empty"):
        create_channel(test_host, test_token)
