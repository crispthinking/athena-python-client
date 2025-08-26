"""Base classes for all Athena exceptions."""


class AthenaError(Exception):
    """Base class for all Athena exceptions."""


class InvalidRequestError(AthenaError):
    """Raised when the request is invalid."""

    default_message = "Invalid request"


class InvalidResponseError(AthenaError):
    """Raised when the response is invalid."""

    default_message = "Invalid response"


class InvalidAuthError(AthenaError):
    """Raised when the authentication is invalid."""

    default_message = "auth_token cannot be empty"


class InvalidHostError(AthenaError):
    """Raised when the host is invalid."""

    default_message = "host cannot be empty"


class OAuthError(AthenaError):
    """Raised when OAuth authentication fails."""

    default_message = "OAuth authentication failed"


class TokenExpiredError(AthenaError):
    """Raised when the authentication token has expired."""

    default_message = "Authentication token has expired"


class CredentialError(AthenaError):
    """Raised when there are issues with credential management."""

    default_message = "Credential management error"
