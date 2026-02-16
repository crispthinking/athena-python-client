"""Tests for gRPC channel creation utilities."""
# pyright: reportPrivateUsage = false
# Ideally we don't use private attributes in the tests but hard to test without

import time
from unittest import mock

import httpx
import pytest

from resolver_athena_client.client.channel import (
    CredentialHelper,
    _AutoRefreshTokenAuthMetadataPlugin,
    create_channel_with_credentials,
)
from resolver_athena_client.client.exceptions import (
    CredentialError,
    InvalidHostError,
    OAuthError,
)


@pytest.mark.asyncio
async def test_create_channel_with_credentials_validation() -> None:
    """Test channel creation with credentials validates input properly."""
    test_host = ""  # Invalid host

    mock_helper = mock.Mock(spec=CredentialHelper)

    with pytest.raises(InvalidHostError, match="host cannot be empty"):
        _ = await create_channel_with_credentials(test_host, mock_helper)


@pytest.mark.asyncio
async def test_create_channel_does_not_eagerly_fetch_token() -> None:
    """Channel creation must NOT call get_token() eagerly."""
    test_host = "test-host:50051"

    mock_helper = mock.Mock(spec=CredentialHelper)

    with (
        mock.patch("grpc.ssl_channel_credentials"),
        mock.patch("grpc.metadata_call_credentials"),
        mock.patch("grpc.composite_channel_credentials"),
        mock.patch("grpc.aio.secure_channel"),
    ):
        _ = await create_channel_with_credentials(test_host, mock_helper)

        # Token should NOT be fetched at channel creation time
        mock_helper.get_token.assert_not_called()


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
        assert helper._audience == "crisp-athena-live"
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
        """Test CredentialHelper initialization with empty client_id."""
        with pytest.raises(CredentialError, match="client_id cannot be empty"):
            _ = CredentialHelper(
                client_id="",
                client_secret="test_client_secret",
            )

    def test_init_with_empty_client_secret(self) -> None:
        """Test CredentialHelper initialization with empty client_secret."""
        with pytest.raises(
            CredentialError, match="client_secret cannot be empty"
        ):
            _ = CredentialHelper(
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
        """Test _is_token_valid returns False when token expires soon."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        helper._token = "test_token"
        helper._token_expires_at = time.time() + 20  # Expires in 20 seconds

        assert not helper._is_token_valid()

    def test_get_token_success(self) -> None:
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

        with mock.patch("httpx.Client") as mock_client:
            mock_response_obj = mock_client.return_value.__enter__.return_value
            mock_response_obj.post.return_value = mock_response

            token = helper.get_token()

            assert token == "new_access_token"
            assert helper._token == "new_access_token"
            assert helper._token_expires_at is not None

    def test_get_token_cached(self) -> None:
        """Test that cached token is returned when valid."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        # Set up a valid cached token
        helper._token = "cached_token"
        helper._token_expires_at = time.time() + 3600

        token = helper.get_token()

        assert token == "cached_token"

    def test_refresh_token_http_error(self) -> None:
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

        with mock.patch("httpx.Client") as mock_client:
            mock_response_obj = mock_client.return_value.__enter__.return_value
            mock_response_obj.post.side_effect = http_error

            with pytest.raises(
                OAuthError, match="OAuth request failed with status 401"
            ):
                _ = helper.get_token()

    def test_refresh_token_request_error(self) -> None:
        """Test token refresh with request error."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        request_error = httpx.RequestError("Connection failed")

        with mock.patch("httpx.Client") as mock_client:
            mock_response_obj = mock_client.return_value.__enter__.return_value
            mock_response_obj.post.side_effect = request_error

            with pytest.raises(
                OAuthError, match="Failed to connect to OAuth server"
            ):
                _ = helper.get_token()

    def test_refresh_token_invalid_response(self) -> None:
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

        with mock.patch("httpx.Client") as mock_client:
            mock_response_obj = mock_client.return_value.__enter__.return_value
            mock_response_obj.post.return_value = mock_response

            with pytest.raises(
                OAuthError, match="Invalid OAuth response format"
            ):
                _ = helper.get_token()

    def test_invalidate_token(self) -> None:
        """Test token invalidation."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        # Set up a valid token
        helper._token = "valid_token"
        helper._token_expires_at = time.time() + 3600

        helper.invalidate_token()

        assert helper._token is None
        assert helper._token_expires_at is None

    def test_get_token_refreshes_after_invalidation(self) -> None:
        """Test that get_token refreshes after invalidation."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        # Set up a valid token, then invalidate it
        helper._token = "old_token"
        helper._token_expires_at = time.time() + 3600
        helper.invalidate_token()

        mock_response = mock.Mock()
        mock_response.json.return_value = {
            "access_token": "refreshed_token",
            "expires_in": 3600,
        }
        mock_response.raise_for_status.return_value = None

        with mock.patch("httpx.Client") as mock_client:
            mock_response_obj = mock_client.return_value.__enter__.return_value
            mock_response_obj.post.return_value = mock_response

            token = helper.get_token()

        assert token == "refreshed_token"


class TestAutoRefreshTokenAuthMetadataPlugin:
    """Tests for the per-RPC auth metadata plugin."""

    def test_plugin_passes_bearer_token_to_callback(self) -> None:
        """Plugin fetches token and passes Bearer metadata."""
        mock_helper = mock.Mock(spec=CredentialHelper)
        mock_helper.get_token.return_value = "test-bearer-token"

        plugin = _AutoRefreshTokenAuthMetadataPlugin(mock_helper)
        mock_callback = mock.Mock()
        mock_context = mock.Mock()

        plugin(mock_context, mock_callback)

        mock_helper.get_token.assert_called_once()
        expected_metadata = (("authorization", "Bearer test-bearer-token"),)
        mock_callback.assert_called_once_with(expected_metadata, None)

    def test_plugin_passes_oauth_error_to_callback(self) -> None:
        """Test that OAuthError is forwarded to the callback as an error."""
        mock_helper = mock.Mock(spec=CredentialHelper)
        oauth_error = OAuthError("token acquisition failed")
        mock_helper.get_token.side_effect = oauth_error

        plugin = _AutoRefreshTokenAuthMetadataPlugin(mock_helper)
        mock_callback = mock.Mock()
        mock_context = mock.Mock()

        plugin(mock_context, mock_callback)

        mock_callback.assert_called_once_with(None, oauth_error)


@pytest.mark.asyncio
async def test_create_channel_with_credentials_invalid_host() -> None:
    """Test channel creation with credentials and invalid host raises error."""
    test_host = ""  # Invalid host

    mock_helper = mock.Mock(spec=CredentialHelper)

    with pytest.raises(InvalidHostError, match="host cannot be empty"):
        _ = await create_channel_with_credentials(test_host, mock_helper)
