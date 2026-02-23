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

    @pytest.mark.parametrize(
        "invalid",
        [-0.1, 1.1, -0.5, 2.0],
    )
    def test_init_with_invalid_proactive_refresh_threshold(
        self, invalid: float
    ) -> None:
        with pytest.raises(
            ValueError,
            match="proactive_refresh_threshold must be a float between 0 and 1",
        ):
            _ = CredentialHelper(
                client_id="test_client_id",
                client_secret="test_client_secret",
                proactive_refresh_threshold=invalid,
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
            issued_at=time.time() - 3700,
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
            issued_at=time.time(),
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
            issued_at=time.time() - 3580,
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

    def test_get_token_preserves_server_casing(self) -> None:
        """Test that server-provided token_type casing is preserved."""
        test_cases = [
            ("Bearer", "Bearer"),
            ("bearer", "bearer"),
            ("BEARER", "BEARER"),
            ("DPoP", "DPoP"),
            ("dpop", "dpop"),
            ("  Bearer  ", "Bearer"),  # Whitespace is stripped
        ]

        for server_type, expected_scheme in test_cases:
            helper = CredentialHelper(
                client_id="test_client_id",
                client_secret="test_client_secret",
            )

            mock_response = mock.Mock()
            mock_response.json.return_value = {
                "access_token": "test_token",
                "expires_in": 3600,
                "token_type": server_type,
            }
            mock_response.raise_for_status.return_value = None

            with mock.patch("httpx.Client") as mock_client:
                mock_response_obj = (
                    mock_client.return_value.__enter__.return_value
                )
                mock_response_obj.post.return_value = mock_response

                token_data = helper.get_token()

                assert token_data.scheme == expected_scheme, (
                    f"Expected {expected_scheme} for {server_type}, "
                    f"got {token_data.scheme}"
                )

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
            issued_at=time.time(),
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
            issued_at=time.time(),
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
            issued_at=time.time(),
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
            issued_at=time.time(),
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
            issued_at=time.time(),
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


class TestBackgroundTokenRefresh:
    """Tests for background token refresh functionality."""

    def test_token_is_old_when_past_halfway_lifetime(self) -> None:
        """Test that a token is considered old when past 25% of its lifetime."""
        current_time = time.time()
        # Token with 1 hour lifetime, 20 minutes remaining (33%)
        token = TokenData(
            access_token="test_token",
            expires_at=current_time + 600,  # 10 minutes from now
            scheme="Bearer",
            issued_at=current_time - 3_000,  # 50 minutes ago
        )
        # Total lifetime = 3600s, remaining = 600s (1/6th), so it's old
        assert token.is_old(0.25)

    def test_token_is_not_old_when_fresh(self) -> None:
        """Test that a token is not old when more than 25% lifetime remains."""
        current_time = time.time()
        # Token with 1 hour lifetime, 40 minutes remaining (67%)
        token = TokenData(
            access_token="test_token",
            expires_at=current_time + 2400,  # 40 minutes from now
            scheme="Bearer",
            issued_at=current_time - 1200,  # 20 minutes ago
        )
        # Total lifetime = 3600s, remaining = 2400s (67%), so it's fresh
        assert not token.is_old(0.25)

    def test_get_token_triggers_background_refresh_for_old_token(self) -> None:
        """Test that get_token triggers background refresh for old tokens."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        current_time = time.time()
        # Set up an old but valid token
        helper._token_data = TokenData(
            access_token="old_token",
            expires_at=current_time + 600,  # 10 minutes from now
            scheme="Bearer",
            issued_at=current_time - 3_000,  # 50 minutes ago
        )

        with mock.patch.object(
            helper, "_start_background_refresh"
        ) as mock_start:
            token_data = helper.get_token()

            # Should return current token immediately
            assert token_data.access_token == "old_token"
            # Should have triggered background refresh
            mock_start.assert_called_once()

    def test_get_token_does_not_trigger_refresh_for_fresh_token(self) -> None:
        """Test that get_token does not trigger refresh for fresh tokens."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        current_time = time.time()
        # Set up a fresh, valid token
        helper._token_data = TokenData(
            access_token="fresh_token",
            expires_at=current_time + 2400,  # 40 minutes remaining
            scheme="Bearer",
            issued_at=current_time - 1200,  # 20 minutes ago, so it's fresh
        )

        with mock.patch.object(
            helper, "_start_background_refresh"
        ) as mock_start:
            token_data = helper.get_token()

            # Should return current token
            assert token_data.access_token == "fresh_token"
            # Should NOT have triggered background refresh
            mock_start.assert_not_called()

    def test_background_refresh_does_not_start_if_already_running(self) -> None:
        """Test that background refresh doesn't start duplicate threads."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        # Mock a running refresh thread
        mock_thread = mock.Mock()
        mock_thread.is_alive.return_value = True
        helper._refresh_thread = mock_thread

        with mock.patch("threading.Thread") as mock_thread_class:
            helper._start_background_refresh()

            # Should not create a new thread
            mock_thread_class.assert_not_called()

    def test_background_refresh_starts_new_thread_if_none_exists(self) -> None:
        """Test that background refresh starts a thread when none exists."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        mock_thread = mock.Mock()
        with mock.patch("threading.Thread", return_value=mock_thread):
            helper._start_background_refresh()

            # Should have started the thread
            mock_thread.start.assert_called_once()

    def test_background_refresh_silently_handles_errors(self) -> None:
        """Test that background refresh silently ignores errors."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        # Mock refresh to raise an error
        with mock.patch.object(
            helper, "_refresh_token", side_effect=OAuthError("Test error")
        ):
            # Should not raise an exception
            helper._background_refresh()

    def test_background_refresh_prevents_stampede(self) -> None:
        """Test background refresh skips refresh if token is fresh."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        current_time = time.time()
        # Set up a fresh token (already refreshed by another thread)
        helper._token_data = TokenData(
            access_token="fresh_token",
            expires_at=current_time + 2400,  # 40 minutes remaining
            scheme="Bearer",
            issued_at=current_time - 1200,  # 20 minutes ago, so it's fresh
        )

        # Mock refresh to track if it's called
        with mock.patch.object(helper, "_refresh_token") as mock_refresh:
            helper._background_refresh()

            # Should NOT have called refresh since token is fresh
            mock_refresh.assert_not_called()

    def test_get_token_blocks_for_expired_token(self) -> None:
        """Test that get_token blocks and refreshes when token is expired."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        # Set up an expired token
        helper._token_data = TokenData(
            access_token="expired_token",
            expires_at=time.time() - 100,  # Expired
            scheme="Bearer",
            issued_at=time.time() - 3700,
        )

        mock_response = mock.Mock()
        mock_response.json.return_value = {
            "access_token": "new_token",
            "expires_in": 3600,
            "token_type": "bearer",
        }
        mock_response.raise_for_status.return_value = None

        with mock.patch("httpx.Client") as mock_client:
            mock_response_obj = mock_client.return_value.__enter__.return_value
            mock_response_obj.post.return_value = mock_response

            token_data = helper.get_token()

            # Should have refreshed and returned new token
            assert token_data.access_token == "new_token"
            # Should have called the OAuth endpoint
            mock_response_obj.post.assert_called_once()

    def test_refresh_token_sets_issued_at(self) -> None:
        """Test that _refresh_token sets the issued_at timestamp."""
        helper = CredentialHelper(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        mock_response = mock.Mock()
        mock_response.json.return_value = {
            "access_token": "new_token",
            "expires_in": 3600,
            "token_type": "bearer",
        }
        mock_response.raise_for_status.return_value = None

        before_time = time.time()
        with mock.patch("httpx.Client") as mock_client:
            mock_response_obj = mock_client.return_value.__enter__.return_value
            mock_response_obj.post.return_value = mock_response

            _ = helper.get_token()

        after_time = time.time()

        # Check that issued_at was set to a reasonable value
        assert helper._token_data is not None
        assert before_time <= helper._token_data.issued_at <= after_time
        # Check that expires_at is approximately issued_at + 3600
        # Allow 1 second tolerance for test execution time
        assert (
            helper._token_data.expires_at - helper._token_data.issued_at - 3600
            < 1
        )
