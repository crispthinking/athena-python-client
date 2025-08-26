"""Athena Client.

This module provides a client for interacting with the Athena API.
"""

from athena_client.client.channel import (
    CredentialHelper,
    create_channel,
    create_channel_with_credentials,
)
from athena_client.client.exceptions import (
    CredentialError,
    OAuthError,
    TokenExpiredError,
)

__all__ = [
    "CredentialError",
    "CredentialHelper",
    "OAuthError",
    "TokenExpiredError",
    "create_channel",
    "create_channel_with_credentials",
]
