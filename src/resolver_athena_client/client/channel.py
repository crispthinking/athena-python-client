"""Channel creation utilities for the Athena client."""

import asyncio
import json
import time
from typing import override

import grpc
import httpx
from grpc.aio import Channel

from resolver_athena_client.client.exceptions import (
    CredentialError,
    InvalidHostError,
    OAuthError,
)


class TokenMetadataPlugin(grpc.AuthMetadataPlugin):
    """Plugin that adds authorization token to gRPC metadata."""

    def __init__(self, token: str) -> None:
        """Initialize the plugin with the auth token.

        Args:
        ----
            token: The authorization token to add to requests

        """
        self._token: str = token

    @override
    def __call__(
        self,
        _: grpc.AuthMetadataContext,
        callback: grpc.AuthMetadataPluginCallback,
    ) -> None:
        """Pass authentication metadata to the provided callback.

        This method will be invoked asynchronously in a separate thread.

        Args:
        ----
            callback: An AuthMetadataPluginCallback to be invoked either
            synchronously or asynchronously.

        """
        metadata = (("authorization", f"Token {self._token}"),)
        callback(metadata, None)


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
        self._token: str | None = None
        self._token_expires_at: float | None = None
        self._lock: asyncio.Lock = asyncio.Lock()

    async def get_token(self) -> str:
        """Get a valid authentication token.

        This method will return a cached token if it's still valid,
        or fetch a new token if needed.

        Returns
        -------
            A valid authentication token

        Raises
        ------
            OAuthError: If token acquisition fails
            TokenExpiredError: If token has expired and refresh fails

        """
        async with self._lock:
            if self._is_token_valid():
                if self._token is None:
                    msg = "Token should be valid but is None"
                    raise RuntimeError(msg)
                return self._token

            await self._refresh_token()
            if self._token is None:
                msg = "Token refresh failed"
                raise RuntimeError(msg)
            return self._token

    def _is_token_valid(self) -> bool:
        """Check if the current token is valid and not expired.

        Returns
        -------
            True if token is valid, False otherwise

        """
        if not self._token or not self._token_expires_at:
            return False

        # Add 30 second buffer before expiration
        return time.time() < (self._token_expires_at - 30)

    async def _refresh_token(self) -> None:
        """Refresh the authentication token by making an OAuth request.

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
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._auth_url,
                    json=payload,
                    headers=headers,
                    timeout=30.0,
                )
                _ = response.raise_for_status()

                token_data = response.json()
                self._token = token_data["access_token"]
                expires_in = token_data.get(
                    "expires_in", 3600
                )  # Default 1 hour
                self._token_expires_at = time.time() + expires_in

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

    async def invalidate_token(self) -> None:
        """Invalidate the current token to force a refresh on next use."""
        async with self._lock:
            self._token = None
            self._token_expires_at = None


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
        OAuthError: If OAuth authentication fails

    """
    if not host:
        raise InvalidHostError(InvalidHostError.default_message)

    # Get a valid token from the credential helper
    token = await credential_helper.get_token()

    # Create credentials with token authentication
    credentials = grpc.composite_channel_credentials(
        grpc.ssl_channel_credentials(),
        grpc.access_token_call_credentials(token),
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
