"""Utility functions for handling classification responses and errors."""

import logging
from typing import TYPE_CHECKING

from resolver_athena_client.client.exceptions import ClassificationOutputError

if TYPE_CHECKING:
    from resolver_athena_client.generated.athena.models_pb2 import (
        ClassificationOutput,
        ClassifyResponse,
    )

logger = logging.getLogger(__name__)


def process_classification_outputs(
    response: "ClassifyResponse",
    *,
    raise_on_error: bool = False,
    log_errors: bool = True,
) -> list["ClassificationOutput"]:
    """Process classification outputs from a response, handling errors properly.

    Args:
    ----
        response: The ClassifyResponse containing outputs to process
        raise_on_error: If True, raises ClassificationOutputError when an output
            contains an error. If False, logs the error and skips the output.
        log_errors: If True, logs error information for failed outputs

    Returns:
    -------
        List of successful ClassificationOutput objects (excludes outputs with
        errors when raise_on_error=False)

    Raises:
    ------
        ClassificationOutputError: When raise_on_error=True and an output
            contains an error

    """
    successful_outputs: list[ClassificationOutput] = []

    for output in response.outputs:
        if output.error and output.error.message:
            error_msg = (
                f"Classification failed for {output.correlation_id[:8]}: "
                f"{output.error.message}"
            )
            if output.error.details:
                error_msg += f" ({output.error.details})"

            if log_errors:
                logger.error(
                    "Output error [%s]: %s (code: %s)",
                    output.correlation_id[:8],
                    output.error.message,
                    output.error.code,
                )

            if raise_on_error:
                raise ClassificationOutputError(
                    correlation_id=output.correlation_id,
                    error=output.error,
                )
            # Skip this output if not raising
            continue

        successful_outputs.append(output)

    return successful_outputs


def get_output_error_summary(response: "ClassifyResponse") -> dict[str, int]:
    """Get a summary of error types in the response outputs.

    Args:
    ----
        response: The ClassifyResponse to analyze

    Returns:
    -------
        Dictionary mapping error code names to their counts

    """
    error_counts: dict[str, int] = {}

    for output in response.outputs:
        if output.error and output.error.message:
            error_code_name = str(output.error.code)
            error_counts[error_code_name] = (
                error_counts.get(error_code_name, 0) + 1
            )

    return error_counts


def has_output_errors(response: "ClassifyResponse") -> bool:
    """Check if any outputs in the response contain errors.

    Args:
    ----
        response: The ClassifyResponse to check

    Returns:
    -------
        True if any output contains an error, False otherwise

    """
    return any(
        output.error and output.error.message for output in response.outputs
    )


def get_successful_outputs(
    response: "ClassifyResponse",
) -> list["ClassificationOutput"]:
    """Get only the successful outputs from a response, filtering out errors.

    Args:
    ----
        response: The ClassifyResponse to filter

    Returns:
    -------
        List of ClassificationOutput objects that don't contain errors

    """
    return [
        output
        for output in response.outputs
        if not (output.error and output.error.message)
    ]


def log_output_errors(response: "ClassifyResponse") -> None:
    """Log all output errors in a response for debugging purposes.

    Args:
    ----
        response: The ClassifyResponse to analyze for errors

    """
    for output in response.outputs:
        if output.error and output.error.message:
            logger.error(
                "Classification error [%s]: %s (code: %s)",
                output.correlation_id[:8],
                output.error.message,
                output.error.code,
            )
            if output.error.details:
                logger.debug(
                    "Error details [%s]: %s",
                    output.correlation_id[:8],
                    output.error.details,
                )
