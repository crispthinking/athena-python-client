"""Channel creation utilities for the Athena client."""

import json
import logging
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

logger = logging.getLogger(__name__)


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
    issued_at: float

    def is_valid(self) -> bool:
        """Check if this token is still valid (with a 30-second buffer)."""
        return time.time() < (self.expires_at - 30)

    def is_old(self) -> bool:
        """Check if this token should be proactively refreshed.

        A token is considered "old" if less than 25% of its lifetime remains.
        This allows background refresh to happen before expiry while the token
        is still usable.
        """
        current_time = time.time()
        total_lifetime = self.expires_at - self.issued_at
        time_remaining = self.expires_at - current_time
        return time_remaining < (total_lifetime * 0.25)


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
        self._refresh_thread: threading.Thread | None = None

    def get_token(self) -> TokenData:
        """Get valid token data, refreshing if necessary.

        Returns
        -------
            A valid ``TokenData`` containing access token, expiry, and scheme

        Raises
        ------
            OAuthError: If token acquisition fails
            RuntimeError: If token is unexpectedly None after refresh

        """
        token_data = self._token_data

        # Fast path: token is valid and fresh
        if token_data is not None and token_data.is_valid():
            # If token is old, trigger background refresh
            if token_data.is_old():
                self._start_background_refresh()
            return token_data

        # Slow path: token is expired or missing, must block
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

    def _start_background_refresh(self) -> None:
        """Start a background thread to refresh the token.

        Only starts a new thread if one isn't already running.

        This method is safe to call multiple times - it only starts a new
        thread if no refresh is currently in progress.
        """
        # Quick check without lock - if refresh thread exists and is
        # alive, skip
        if self._refresh_thread is not None and self._refresh_thread.is_alive():
            return

        # Try to acquire lock and start refresh
        if self._lock.acquire(blocking=False):
            try:
                # Double-check: another thread might have started refresh,
                # or the token may have been refreshed.
                refresh_not_active = (
                    self._refresh_thread is None
                    or not self._refresh_thread.is_alive()
                )
                token_needs_refresh = (
                    self._token_data is None or self._token_data.is_old()
                )
                refresh_needed = refresh_not_active and token_needs_refresh
                if refresh_needed:
                    self._refresh_thread = threading.Thread(
                        target=self._background_refresh,
                        daemon=True,
                    )
                    self._refresh_thread.start()
            finally:
                self._lock.release()

    def _background_refresh(self) -> None:
        """Background thread target for token refresh.

        Acquires the lock and refreshes the token. Errors are logged
        but silently ignored since the next foreground request will
        retry if needed.
        """
        with self._lock:
            # Check if token still needs refresh (prevent stampede)
            token_data = self._token_data
            if token_data is not None and not token_data.is_old():
                # Token was already refreshed by another thread
                return

            try:
                self._refresh_token()
            except Exception as e:  # noqa: BLE001
                # Log but don't raise - background refresh failures
                # are recoverable (next get_token() will retry)
                logger.debug(
                    "Background token refresh failed, "
                    "will retry on next request: %s",
                    e,
                )

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
            current_time = time.time()
            self._token_data = TokenData(
                access_token=access_token,
                expires_at=current_time + expires_in,
                scheme=scheme,
                issued_at=current_time,
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
