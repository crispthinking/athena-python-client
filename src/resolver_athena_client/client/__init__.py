"""Athena Client.

This module provides a client for interacting with the Athena API.
"""

from resolver_athena_client.client.channel import (
    CredentialHelper,
    create_channel_with_credentials,
)
from resolver_athena_client.client.exceptions import (
    ClassificationOutputError,
    CredentialError,
    OAuthError,
    TokenExpiredError,
)
from resolver_athena_client.client.utils import (
    get_output_error_summary,
    get_successful_outputs,
    has_output_errors,
    log_output_errors,
    process_classification_outputs,
)

__all__ = [
    "ClassificationOutputError",
    "CredentialError",
    "CredentialHelper",
    "OAuthError",
    "TokenExpiredError",
    "create_channel_with_credentials",
    "get_output_error_summary",
    "get_successful_outputs",
    "has_output_errors",
    "log_output_errors",
    "process_classification_outputs",
]
