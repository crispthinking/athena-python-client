"""Channel creation utilities for the Athena client."""

import grpc
from grpc.aio import Channel


def create_channel(host: str, auth_token: str) -> Channel:
    """Create a gRPC channel with optional authentication.

    Args:
        host: The host address to connect to
        auth_token: Optional authentication token. If provided, creates a secure
            channel with token-based authentication. If not provided, creates an
            insecure channel.

    Returns:
        A gRPC channel (either secure or insecure)

    """
    # Create credentials with token authentication
    credentials = grpc.composite_channel_credentials(
        grpc.ssl_channel_credentials(),
        grpc.access_token_call_credentials(auth_token),
    )

    return grpc.aio.secure_channel(host, credentials)
