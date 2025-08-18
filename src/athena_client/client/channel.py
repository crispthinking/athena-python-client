"""Channel creation utilities for the Athena client."""

import grpc
from grpc.aio import Channel

from athena_client.client.exceptions import InvalidAuthError, InvalidHostError


class TokenMetadataPlugin(grpc.AuthMetadataPlugin):
    """Plugin that adds authorization token to gRPC metadata."""

    def __init__(self, token: str) -> None:
        """Initialize the plugin with the auth token.

        Args:
            token: The authorization token to add to requests

        """
        self._token = token

    def __call__(
        self,
        _: grpc.AuthMetadataContext,
        callback: grpc.AuthMetadataPluginCallback,
    ) -> None:
        """Pass authentication metadata to the provided callback.

        This method will be invoked asynchronously in a separate thread.

        Args:
            callback: An AuthMetadataPluginCallback to be invoked either
            synchronously or asynchronously.

        """
        # Create metadata with token
        metadata = (("Authorization", f"Token {self._token}"),)
        callback(metadata, None)


def create_channel(host: str, auth_token: str) -> Channel:
    """Create a gRPC channel with optional authentication.

    Args:
        host: The host address to connect to
        auth_token: Optional authentication token. If provided, creates a secure
            channel with token-based authentication. If not provided, creates an
            insecure channel.

    Returns:
        A gRPC channel (either secure or insecure)

    Raises:
        InvalidHostError: If host is empty
        InvalidAuthError: If auth_token is empty

    """
    if not host:
        raise InvalidHostError(InvalidHostError.default_message)
    if not auth_token:
        raise InvalidAuthError(InvalidAuthError.default_message)

    # Create credentials with token authentication
    credentials = grpc.composite_channel_credentials(
        grpc.ssl_channel_credentials(),
        grpc.metadata_call_credentials(TokenMetadataPlugin(auth_token)),
    )

    return grpc.aio.secure_channel(host, credentials)
