import logging
import time
import typing
from collections.abc import AsyncIterator

from resolver_athena_client.generated.athena.models_pb2 import (
    ClassificationOutput,
    ClassifyResponse,
)

from resolver_athena_client.client.athena_client import AthenaClient
from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.channel import (
    CredentialHelper,
    create_channel_with_credentials,
)
from resolver_athena_client.client.models.input_model import ImageData
from resolver_athena_client.client.utils import (
    get_output_error_summary,
    has_output_errors,
    process_classification_outputs,
)

T = typing.TypeVar("T")


async def count_and_yield(
    source: AsyncIterator[T], counter: list[int]
) -> AsyncIterator[T]:
    """Wrap an async iterator to count items as they are yielded."""
    async for item in source:
        counter[0] += 1
        yield item


def process_errors(
    logger: logging.Logger, result: ClassifyResponse, current_error_count: int
) -> int:
    """Process errors in the result and update the current error count."""
    if has_output_errors(result):
        error_summary = get_output_error_summary(result)
        result_error_count = sum(error_summary.values())
        current_error_count += result_error_count
        logger.warning(
            "Received %d outputs with errors: %s",
            result_error_count,
            error_summary,
        )
    return current_error_count


def dump_classifications(
    logger: logging.Logger, successful_outputs: list[ClassificationOutput]
) -> None:
    """Dump classifications from successful outputs to the logger."""
    for output in successful_outputs:
        classifications = {
            c.label: round(c.weight, 3) for c in output.classifications
        }
        logger.debug(
            "Result [%s]: %s",
            output.correlation_id[:8],
            classifications,
        )


async def classify_images(
    logger: logging.Logger,
    options: AthenaOptions,
    credential_helper: CredentialHelper,
    max_test_images: int,
    image_generator: AsyncIterator[ImageData],
) -> tuple[int, int, int]:
    """Run example classification with OAuth credential helper.

    Args:
        logger: Logger instance for output
        options: Configuration options for the Athena client
        credential_helper: OAuth credential helper for authentication
        max_test_images: Maximum number of test images to generate

    Returns:
        Number of requests sent and responses received

    """
    channel = await create_channel_with_credentials(
        options.host, credential_helper
    )

    sent_counter = [0]  # Use list to allow mutation in closure
    received_count = 0
    error_count = 0

    async with AthenaClient(channel, options) as client:
        counted_image_generator = count_and_yield(image_generator, sent_counter)
        results = client.classify_images(counted_image_generator)

        start_time = time.time()

        try:
            async for result in results:
                received_count += len(result.outputs)

                if received_count % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = received_count / elapsed if elapsed > 0 else 0
                    logger.info(
                        "Sent %d requests, received %d responses (%.1f/sec)",
                        sent_counter[0],
                        received_count,
                        rate,
                    )

                error_count = process_errors(logger, result, error_count)

                # Process outputs, logging errors but continuing with
                # successful ones
                successful_outputs = process_classification_outputs(
                    result, raise_on_error=False, log_errors=True
                )

                if logger.isEnabledFor(logging.DEBUG):
                    dump_classifications(logger, successful_outputs)

                if received_count >= max_test_images:
                    logger.info(
                        "Received all %s test images, with %d errors.",
                        received_count,
                        error_count,
                    )
                    break

        except Exception:
            logger.exception("Error during classification")
            if received_count == 0:
                raise
        finally:
            duration = time.time() - start_time
            if received_count > 0:
                avg_rate = received_count / duration if duration > 0 else 0
                logger.info(
                    "Completed: sent=%d received=%d errors=%d in %.1fs "
                    "(%.1f/sec)",
                    sent_counter[0],
                    received_count,
                    error_count,
                    duration,
                    avg_rate,
                )

                if options.timeout and duration >= options.timeout * 0.95:
                    logger.info(
                        "Stream reached maximum duration: %.1fs (limit: %.1fs)",
                        duration,
                        options.timeout,
                    )
                elif options.timeout:
                    logger.info(
                        "Stream completed naturally in %.1fs (max: %.1fs)",
                        duration,
                        options.timeout,
                    )

    return (sent_counter[0], received_count, error_count)


async def classify_images_break_on_first_result(
    logger: logging.Logger,
    options: AthenaOptions,
    credential_helper: CredentialHelper,
    image_generator: AsyncIterator[ImageData],
) -> tuple[int, int, int]:
    """Run example classification with OAuth credential helper.

    Args:
        logger: Logger instance for output
        options: Configuration options for the Athena client
        credential_helper: OAuth credential helper for authentication
        image_generator: Async iterator of ImageData objects

    Returns:
        Number of requests sent and responses received

    """
    channel = await create_channel_with_credentials(
        options.host, credential_helper
    )

    sent_counter = [0]  # Use list to allow mutation in closure
    received_count = 0
    error_count = 0

    async with AthenaClient(channel, options) as client:
        counted_image_generator = count_and_yield(image_generator, sent_counter)
        results = client.classify_images(counted_image_generator)

        start_time = time.time()

        try:
            async for result in results:
                received_count += len(result.outputs)

                if received_count % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = received_count / elapsed if elapsed > 0 else 0
                    logger.info(
                        "Sent %d requests, received %d responses (%.1f/sec)",
                        sent_counter[0],
                        received_count,
                        rate,
                    )

                error_count = process_errors(logger, result, error_count)
                break

        except Exception:
            logger.exception("Error during classification")
            if received_count == 0:
                raise

    return (sent_counter[0], received_count, error_count)
