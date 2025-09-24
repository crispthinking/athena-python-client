"""Base classes for all Athena exceptions."""

from typing import TYPE_CHECKING, final

if TYPE_CHECKING:
    from resolver_athena_client.generated.athena.models_pb2 import (
        ClassificationError,
    )


class AthenaError(Exception):
    """Base class for all Athena exceptions."""


class InvalidRequestError(AthenaError):
    """Raised when the request is invalid."""

    default_message: str = "Invalid request"


class InvalidResponseError(AthenaError):
    """Raised when the response is invalid."""

    default_message: str = "Invalid response"


class InvalidAuthError(AthenaError):
    """Raised when the authentication is invalid."""

    default_message: str = "auth_token cannot be empty"


class InvalidHostError(AthenaError):
    """Raised when the host is invalid."""

    default_message: str = "host cannot be empty"


class OAuthError(AthenaError):
    """Raised when OAuth authentication fails."""

    default_message: str = "OAuth authentication failed"


class TokenExpiredError(AthenaError):
    """Raised when the authentication token has expired."""

    default_message: str = "Authentication token has expired"


class CredentialError(AthenaError):
    """Raised when there are issues with credential management."""

    default_message: str = "Credential management error"


@final
class ClassificationOutputError(AthenaError):
    """Raised when an individual classification output contains an error."""

    def __init__(
        self,
        correlation_id: str,
        error: "ClassificationError",
        message: str | None = None,
    ) -> None:
        """Initialize the classification output error.

        Args:
        ----
            correlation_id: The correlation ID of the failed output
            error: The ClassificationError from the protobuf response
            message: Optional custom error message

        """
        self.correlation_id = correlation_id
        self.error_code = error.code
        self.error_message = error.message
        self.error_details = error.details

        if message is None:
            message = (
                f"Classification failed for {correlation_id[:8]}: "
                f"{error.message}"
            )
            if error.details:
                message += f" ({error.details})"

        super().__init__(message)
