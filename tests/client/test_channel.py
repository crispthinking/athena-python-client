"""Tests for gRPC channel creation utilities."""

import time
from unittest import mock

import httpx
import pytest
from grpc.aio import Channel

from athena_client.client.channel import (
    CredentialHelper,
    create_channel,
    create_channel_with_credentials,
)
from athena_client.client.exceptions import (
    CredentialError,
    InvalidAuthError,
    InvalidHostError,
    OAuthError,
)


def test_create_channel() -> None:
    """Test channel creation with authentication token."""
    test_host = "test-host:50051"
    test_token = "test-token"

    # Mock the credentials and channel creation
    mock_credentials = mock.Mock()
    mock_channel = mock.Mock(spec=Channel)

    with (
        mock.patch("grpc.ssl_channel_credentials") as mock_ssl_creds,
        mock.patch("grpc.access_token_call_credentials") as mock_token_creds,
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
        mock_token_creds.assert_called_once_with(test_token)
        mock_composite_creds.assert_called_once_with(
            mock_ssl_creds.return_value, mock_token_creds.return_value
        )
        mock_secure_channel.assert_called_once_with(
            test_host, mock_credentials, options=mock.ANY
        )


def test_create_channel_with_invalid_host() -> None:
    """Test channel creation with invalid host raises error."""
    test_host = ""  # Invalid host
    test_token = "test-token"

    with pytest.raises(InvalidHostError, match="host cannot be empty"):
        create_channel(test_host, test_token)


def test_create_channel_with_empty_token() -> None:
    """Test channel creation with empty auth token raises error."""
    test_host = "test-host:50051"
    test_token = ""  # Empty token

    with pytest.raises(InvalidAuthError, match="auth_token cannot be empty"):
        create_channel(test_host, test_token)


class TestCredentialHelper:
    """Test cases for CredentialHelper OAuth functionality."""

    def test_init_with_valid_params(self) -> None:
        """Test CredentialHelper initialization with valid parameters."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        assert helper._client_id == "test_client_id"
        assert helper._client_secret == "test_client_secret"
        assert helper._auth_url == "https://crispthinking.auth0.com/oauth/token"
        assert helper._audience == "crisp-athena-dev"
        assert helper._token is None
        assert helper._token_expires_at is None

    def test_init_with_custom_params(self) -> None:
        """Test CredentialHelper initialization with custom parameters."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
            auth_url="https://custom.auth0.com/oauth/token",
            audience="custom-audience",
        )

        assert helper._auth_url == "https://custom.auth0.com/oauth/token"
        assert helper._audience == "custom-audience"

    def test_init_with_empty_client_id(self) -> None:
        """Test CredentialHelper initialization with empty client_id raises error."""
        with pytest.raises(CredentialError, match="client_id cannot be empty"):
            CredentialHelper(
                client_id="",
                client_secret="test_client_secret",
            )

    def test_init_with_empty_client_secret(self) -> None:
        """Test CredentialHelper initialization with empty client_secret raises error."""
        with pytest.raises(
            CredentialError, match="client_secret cannot be empty"
        ):
            CredentialHelper(
                client_id="test_client_id",
                client_secret="",
            )

    def test_is_token_valid_with_no_token(self) -> None:
        """Test _is_token_valid returns False when no token is set."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        assert not helper._is_token_valid()

    def test_is_token_valid_with_expired_token(self) -> None:
        """Test _is_token_valid returns False when token is expired."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        helper._token = "test_token"
        helper._token_expires_at = time.time() - 100  # Expired

        assert not helper._is_token_valid()

    def test_is_token_valid_with_valid_token(self) -> None:
        """Test _is_token_valid returns True when token is valid."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        helper._token = "test_token"
        helper._token_expires_at = time.time() + 3600  # Valid for 1 hour

        assert helper._is_token_valid()

    def test_is_token_valid_with_soon_expiring_token(self) -> None:
        """Test _is_token_valid returns False when token expires soon (within 30s)."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        helper._token = "test_token"
        helper._token_expires_at = time.time() + 20  # Expires in 20 seconds

        assert not helper._is_token_valid()

    @pytest.mark.asyncio
    async def test_get_token_success(self) -> None:
        """Test successful token acquisition."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        mock_response = mock.Mock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "expires_in": 3600,
        }
        mock_response.raise_for_status.return_value = None

        with mock.patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

            token = await helper.get_token()

            assert token == "new_access_token"
            assert helper._token == "new_access_token"
            assert helper._token_expires_at is not None

    @pytest.mark.asyncio
    async def test_get_token_cached(self) -> None:
        """Test that cached token is returned when valid."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        # Set up a valid cached token
        helper._token = "cached_token"
        helper._token_expires_at = time.time() + 3600

        token = await helper.get_token()

        assert token == "cached_token"

    @pytest.mark.asyncio
    async def test_refresh_token_http_error(self) -> None:
        """Test token refresh with HTTP error."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        mock_response = mock.Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": "invalid_client",
            "error_description": "Invalid client credentials",
        }

        http_error = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=mock.Mock(),
            response=mock_response,
        )

        with mock.patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = http_error

            with pytest.raises(
                OAuthError, match="OAuth request failed with status 401"
            ):
                await helper.get_token()

    @pytest.mark.asyncio
    async def test_refresh_token_request_error(self) -> None:
        """Test token refresh with request error."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        request_error = httpx.RequestError("Connection failed")

        with mock.patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = request_error

            with pytest.raises(
                OAuthError, match="Failed to connect to OAuth server"
            ):
                await helper.get_token()

    @pytest.mark.asyncio
    async def test_refresh_token_invalid_response(self) -> None:
        """Test token refresh with invalid response format."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        mock_response = mock.Mock()
        mock_response.json.return_value = {
            "invalid_field": "missing_access_token",
        }
        mock_response.raise_for_status.return_value = None

        with mock.patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

            with pytest.raises(
                OAuthError, match="Invalid OAuth response format"
            ):
                await helper.get_token()

    @pytest.mark.asyncio
    async def test_invalidate_token(self) -> None:
        """Test token invalidation."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        # Set up a valid token
        helper._token = "valid_token"
        helper._token_expires_at = time.time() + 3600

        await helper.invalidate_token()

        assert helper._token is None
        assert helper._token_expires_at is None


@pytest.mark.asyncio
async def test_create_channel_with_credentials_success() -> None:
    """Test successful channel creation with credential helper."""
    test_host = "test-host:50051"

    mock_helper = mock.Mock(spec=CredentialHelper)
    mock_helper.get_token.return_value = "test_token"

    mock_credentials = mock.Mock()
    mock_channel = mock.Mock(spec=Channel)

    with (
        mock.patch("grpc.ssl_channel_credentials") as mock_ssl_creds,
        mock.patch("grpc.access_token_call_credentials") as mock_token_creds,
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
        channel = await create_channel_with_credentials(test_host, mock_helper)

        # Verify channel creation
        assert channel == mock_channel
        mock_helper.get_token.assert_called_once()
        mock_token_creds.assert_called_once_with("test_token")


@pytest.mark.asyncio
async def test_create_channel_with_credentials_invalid_host() -> None:
    """Test channel creation with credentials and invalid host raises error."""
    test_host = ""  # Invalid host

    mock_helper = mock.Mock(spec=CredentialHelper)

    with pytest.raises(InvalidHostError, match="host cannot be empty"):
        await create_channel_with_credentials(test_host, mock_helper)


@pytest.mark.asyncio
async def test_create_channel_with_credentials_oauth_error() -> None:
    """Test channel creation with credentials when OAuth fails."""
    test_host = "test-host:50051"

    mock_helper = mock.Mock(spec=CredentialHelper)
    mock_helper.get_token.side_effect = OAuthError("OAuth failed")

    with pytest.raises(OAuthError, match="OAuth failed"):
        await create_channel_with_credentials(test_host, mock_helper)
