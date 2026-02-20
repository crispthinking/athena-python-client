"""Channel creation utilities for the Athena client."""

import json
import threading
import time
from typing import NamedTuple, override

import grpc
import httpx
from grpc.aio import Channel

from resolver_athena_client.client.exceptions import (
    CredentialError,
    InvalidHostError,
    OAuthError,
)


class TokenData(NamedTuple):
    """Immutable snapshot of token state.

    Storing token, expiry, and scheme together as a single object
    ensures that validity checks and token reads are always consistent,
    eliminating TOCTOU races between ``get_token`` and
    ``invalidate_token``.
    """

    access_token: str
    expires_at: float
    scheme: str

    def is_valid(self) -> bool:
        """Check if this token is still valid (with a 30-second buffer)."""
        return time.time() < (self.expires_at - 30)


class CredentialHelper:
    """OAuth credential helper for managing authentication tokens."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        auth_url: str = "https://crispthinking.auth0.com/oauth/token",
        audience: str = "crisp-athena-live",
    ) -> None:
        """Initialize the credential helper.

        Args:
        ----
            client_id: OAuth client ID
            client_secret: OAuth client secret
            auth_url: OAuth token endpoint URL
            audience: OAuth audience

        """
        if not client_id:
            msg = "client_id cannot be empty"
            raise CredentialError(msg)
        if not client_secret:
            msg = "client_secret cannot be empty"
            raise CredentialError(msg)

        self._client_id: str = client_id
        self._client_secret: str = client_secret
        self._auth_url: str = auth_url
        self._audience: str = audience
        self._token_data: TokenData | None = None
        self._lock: threading.Lock = threading.Lock()

    def get_token(self) -> TokenData:
        """Get valid token data, refreshing if necessary.

        Uses double-checked locking: the happy path (token is valid)
        avoids acquiring the lock entirely.  The lock is only taken
        when the token needs to be refreshed.

        Returns
        -------
            A valid ``TokenData`` containing access token, expiry, and scheme

        Raises
        ------
            OAuthError: If token acquisition fails
            RuntimeError: If token is unexpectedly None after refresh

        """
        token_data = self._token_data
        if token_data is not None and token_data.is_valid():
            return token_data

        with self._lock:
            token_data = self._token_data
            if token_data is not None and token_data.is_valid():
                return token_data

            self._refresh_token()

            token_data = self._token_data
            if token_data is None:
                msg = "Token is unexpectedly None after refresh"
                raise RuntimeError(msg)
            return token_data

    def _refresh_token(self) -> None:
        """Refresh the authentication token by making an OAuth request.

        This is a synchronous call (suitable for the gRPC metadata-plugin
        thread) and must be called while ``self._lock`` is held.

        Raises
        ------
            OAuthError: If the OAuth request fails

        """
        payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "audience": self._audience,
            "grant_type": "client_credentials",
        }

        headers = {"content-type": "application/json"}

        try:
            with httpx.Client() as client:
                response = client.post(
                    self._auth_url,
                    json=payload,
                    headers=headers,
                    timeout=30.0,
                )
                _ = response.raise_for_status()

            raw = response.json()
            access_token: str = raw["access_token"]
            expires_in: int = raw.get("expires_in", 3600)  # Default 1 hour
            token_type = raw.get("token_type", "Bearer")
            # Preserve server-provided casing, only strip whitespace
            scheme: str = token_type.strip() if token_type else "Bearer"
            self._token_data = TokenData(
                access_token=access_token,
                expires_at=time.time() + expires_in,
                scheme=scheme,
            )

        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_data = e.response.json()
                error_desc = error_data.get(
                    "error_description", error_data.get("error", "")
                )
                error_detail = f": {error_desc}"
            except (json.JSONDecodeError, KeyError):
                pass

            msg = (
                f"OAuth request failed with status "
                f"{e.response.status_code}{error_detail}"
            )
            raise OAuthError(msg) from e

        except (httpx.RequestError, httpx.TimeoutException) as e:
            msg = f"Failed to connect to OAuth server: {e}"
            raise OAuthError(msg) from e

        except KeyError as e:
            msg = f"Invalid OAuth response format: missing {e}"
            raise OAuthError(msg) from e

        except Exception as e:
            msg = f"Unexpected error during OAuth: {e}"
            raise OAuthError(msg) from e

    def invalidate_token(self) -> None:
        """Invalidate the current token to force a refresh on next use."""
        with self._lock:
            self._token_data = None


class _AutoRefreshTokenAuthMetadataPlugin(grpc.AuthMetadataPlugin):
    """gRPC auth plugin that fetches a fresh token for every RPC.

    The plugin delegates to ``CredentialHelper.get_token()`` which
    handles caching, expiry checks, and thread-safe refresh internally.
    This callback is invoked by gRPC on a *separate* thread, so the
    underlying ``CredentialHelper`` must use ``threading.Lock`` (not
    ``asyncio.Lock``).
    """

    def __init__(self, credential_helper: CredentialHelper) -> None:
        """Initialize with a credential helper.

        Args:
        ----
            credential_helper: The helper that manages token lifecycle

        """
        self._credential_helper: CredentialHelper = credential_helper

    @override
    def __call__(
        self,
        _: grpc.AuthMetadataContext,
        callback: grpc.AuthMetadataPluginCallback,
    ) -> None:
        """Supply authorization metadata for an RPC.

        Called by the gRPC runtime on a background thread before each
        RPC.  On success the token is forwarded using the scheme from
        the OAuth token response (typically ``Bearer``); on failure
        the error is passed to the callback so gRPC can surface it as
        an RPC error.

        Args:
        ----
            callback: gRPC callback to receive metadata or an error

        """
        try:
            token_data = self._credential_helper.get_token()
            scheme = token_data.scheme
            token = token_data.access_token
            metadata = (("authorization", f"{scheme} {token}"),)
            callback(metadata, None)
        except Exception as err:  # noqa: BLE001
            callback((), err)


async def create_channel_with_credentials(
    host: str,
    credential_helper: CredentialHelper,
) -> Channel:
    """Create a gRPC channel with OAuth credential helper.

    Args:
    ----
        host: The host address to connect to
        credential_helper: The credential helper for OAuth authentication

    Returns:
    -------
        A secure gRPC channel with OAuth authentication

    Raises:
    ------
        InvalidHostError: If host is empty

    Note:
    ----
        OAuth errors are no longer raised at channel-creation time.
        Instead, they surface as RPC errors when the per-request auth
        metadata plugin attempts to acquire a token.

    """
    if not host:
        raise InvalidHostError(InvalidHostError.default_message)

    # Create credentials with per-RPC token refresh
    credentials = grpc.composite_channel_credentials(
        grpc.ssl_channel_credentials(),
        grpc.metadata_call_credentials(
            _AutoRefreshTokenAuthMetadataPlugin(credential_helper)
        ),
    )

    # Configure gRPC options for persistent connections
    options = [
        # Keep connections alive longer
        ("grpc.keepalive_time_ms", 60000),  # Send keepalive every 60s
        ("grpc.keepalive_timeout_ms", 30000),  # Wait 30s for keepalive ack
        (
            "grpc.keepalive_permit_without_calls",
            1,
        ),  # Allow keepalive when idle
        # Optimize for persistent streams
        ("grpc.http2.max_pings_without_data", 0),  # Allow unlimited pings
        (
            "grpc.http2.min_time_between_pings_ms",
            60000,
        ),  # Min 60s between pings
        (
            "grpc.http2.min_ping_interval_without_data_ms",
            30000,
        ),  # Min 30s when idle
        # Increase buffer sizes for better performance
        ("grpc.http2.write_buffer_size", 1024 * 1024),  # 1MB write buffer
        (
            "grpc.max_receive_message_length",
            64 * 1024 * 1024,
        ),  # 64MB max message
    ]

    return grpc.aio.secure_channel(host, credentials, options=options)
