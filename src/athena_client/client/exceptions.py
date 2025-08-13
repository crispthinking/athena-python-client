"""Base classes for all Athena exceptions."""


class AthenaError(Exception):
    """Base class for all Athena exceptions."""


class InvalidRequestError(AthenaError):
    """Raised when the request is invalid."""
