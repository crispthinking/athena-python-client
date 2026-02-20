"""Tests for gRPC channel creation utilities."""
# pyright: reportPrivateUsage = false
# Ideally we don't use private attributes in the tests but hard to test without

import time
from unittest import mock

import httpx
import pytest

from resolver_athena_client.client.channel import (
    CredentialHelper,
    TokenData,
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
        assert helper._token_data is None

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
        """Test token is not valid when no token data is set."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        assert helper._token_data is None

    def test_is_token_valid_with_expired_token(self) -> None:
        """Test TokenData.is_valid returns False when token is expired."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        helper._token_data = TokenData(
            access_token="test_token",
            expires_at=time.time() - 100,
            scheme="Bearer",
        )

        assert not helper._token_data.is_valid()

    def test_is_token_valid_with_valid_token(self) -> None:
        """Test TokenData.is_valid returns True when token is valid."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        helper._token_data = TokenData(
            access_token="test_token",
            expires_at=time.time() + 3600,
            scheme="Bearer",
        )

        assert helper._token_data.is_valid()

    def test_is_token_valid_with_soon_expiring_token(self) -> None:
        """Test is_valid returns False when token expires within 30s."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        helper._token_data = TokenData(
            access_token="test_token",
            expires_at=time.time() + 20,
            scheme="Bearer",
        )

        assert not helper._token_data.is_valid()

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
            "token_type": "Bearer",
        }
        mock_response.raise_for_status.return_value = None

        with mock.patch("httpx.Client") as mock_client:
            mock_response_obj = mock_client.return_value.__enter__.return_value
            mock_response_obj.post.return_value = mock_response

            token_data = helper.get_token()

            assert token_data.access_token == "new_access_token"
            assert token_data.scheme == "Bearer"
            assert helper._token_data is not None
            assert helper._token_data.expires_at is not None

    def test_get_token_respects_token_type(self) -> None:
        """Test that token_type from OAuth response is respected."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        mock_response = mock.Mock()
        mock_response.json.return_value = {
            "access_token": "some_token",
            "expires_in": 3600,
            "token_type": "DPoP",
        }
        mock_response.raise_for_status.return_value = None

        with mock.patch("httpx.Client") as mock_client:
            mock_response_obj = mock_client.return_value.__enter__.return_value
            mock_response_obj.post.return_value = mock_response

            token_data = helper.get_token()

            assert token_data.scheme == "DPoP"

    def test_get_token_defaults_to_bearer(self) -> None:
        """Test that scheme defaults to Bearer when token_type is absent."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        mock_response = mock.Mock()
        mock_response.json.return_value = {
            "access_token": "some_token",
            "expires_in": 3600,
        }
        mock_response.raise_for_status.return_value = None

        with mock.patch("httpx.Client") as mock_client:
            mock_response_obj = mock_client.return_value.__enter__.return_value
            mock_response_obj.post.return_value = mock_response

            token_data = helper.get_token()

            assert token_data.scheme == "Bearer"

    def test_get_token_cached(self) -> None:
        """Test that cached token is returned when valid."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        # Set up a valid cached token
        helper._token_data = TokenData(
            access_token="cached_token",
            expires_at=time.time() + 3600,
            scheme="Bearer",
        )

        token_data = helper.get_token()

        assert token_data.access_token == "cached_token"

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
        helper._token_data = TokenData(
            access_token="valid_token",
            expires_at=time.time() + 3600,
            scheme="Bearer",
        )

        helper.invalidate_token()

        assert helper._token_data is None

    def test_get_token_refreshes_after_invalidation(self) -> None:
        """Test that get_token refreshes after invalidation."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        # Set up a valid token, then invalidate it
        helper._token_data = TokenData(
            access_token="old_token",
            expires_at=time.time() + 3600,
            scheme="Bearer",
        )
        helper.invalidate_token()

        mock_response = mock.Mock()
        mock_response.json.return_value = {
            "access_token": "refreshed_token",
            "expires_in": 3600,
            "token_type": "bearer",
        }
        mock_response.raise_for_status.return_value = None

        with mock.patch("httpx.Client") as mock_client:
            mock_response_obj = mock_client.return_value.__enter__.return_value
            mock_response_obj.post.return_value = mock_response

            token_data = helper.get_token()

        assert token_data.access_token == "refreshed_token"


class TestAutoRefreshTokenAuthMetadataPlugin:
    """Tests for the per-RPC auth metadata plugin."""

    def test_plugin_passes_bearer_token_to_callback(self) -> None:
        """Plugin fetches token and passes Bearer metadata."""
        mock_helper = mock.Mock(spec=CredentialHelper)
        mock_helper.get_token.return_value = TokenData(
            access_token="test-bearer-token",
            expires_at=time.time() + 3600,
            scheme="Bearer",
        )

        plugin = _AutoRefreshTokenAuthMetadataPlugin(mock_helper)
        mock_callback = mock.Mock()
        mock_context = mock.Mock()

        plugin(mock_context, mock_callback)

        mock_helper.get_token.assert_called_once()
        expected_metadata = (("authorization", "Bearer test-bearer-token"),)
        mock_callback.assert_called_once_with(expected_metadata, None)

    def test_plugin_respects_token_scheme(self) -> None:
        """Plugin uses the scheme from TokenData, not hardcoded Bearer."""
        mock_helper = mock.Mock(spec=CredentialHelper)
        mock_helper.get_token.return_value = TokenData(
            access_token="dpop-token",
            expires_at=time.time() + 3600,
            scheme="Dpop",
        )

        plugin = _AutoRefreshTokenAuthMetadataPlugin(mock_helper)
        mock_callback = mock.Mock()
        mock_context = mock.Mock()

        plugin(mock_context, mock_callback)

        expected_metadata = (("authorization", "Dpop dpop-token"),)
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

        mock_callback.assert_called_once_with((), oauth_error)

    def test_plugin_catches_unexpected_exceptions(self) -> None:
        """Non-OAuthError exceptions are forwarded to callback."""
        mock_helper = mock.Mock(spec=CredentialHelper)
        runtime_error = RuntimeError("unexpected failure")
        mock_helper.get_token.side_effect = runtime_error

        plugin = _AutoRefreshTokenAuthMetadataPlugin(mock_helper)
        mock_callback = mock.Mock()
        mock_context = mock.Mock()

        plugin(mock_context, mock_callback)

        mock_callback.assert_called_once_with((), runtime_error)
