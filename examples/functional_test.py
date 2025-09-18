#!/usr/bin/env python3
"""Functional test script for image classification using OAuth authentication.

This test is primarily used internally, but is provided here as a further
example of using the Athena client with OAuth.
"""

import asyncio
import logging
import os
import sys
import time
import uuid
from collections.abc import AsyncIterator

from create_image import iter_images
from dotenv import load_dotenv

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
from resolver_athena_client.generated.athena.models_pb2 import (
    ClassificationOutput,
    ClassifyResponse,
)


async def rate_limited_image_iter(
    min_interval_ms: int,
    max_images: int | None = None,
    counter: list[int] | None = None,
) -> AsyncIterator[ImageData]:
    """Generate images with a minimum interval between yields."""
    last_yield_time = time.time()
    async for image in iter_images(max_images, counter):
        elapsed_ms = (time.time() - last_yield_time) * 1000
        if elapsed_ms < min_interval_ms:
            await asyncio.sleep((min_interval_ms - elapsed_ms) / 1000)
        yield image
        last_yield_time = time.time()


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


async def run_smoke_test(
    logger: logging.Logger,
    options: AthenaOptions,
    credential_helper: CredentialHelper,
    max_test_images: int,
    rate_limit_min_interval_ms: int | None = None,
) -> tuple[int, int, int]:
    """Run example classification with OAuth credential helper.

    Args:
        logger: Logger instance for output
        options: Configuration options for the Athena client
        credential_helper: OAuth credential helper for authentication
        max_test_images: Maximum number of test images to generate
        rate_limit_min_interval_ms: Optional minimum interval in milliseconds
            between sending images to control rate. If None, sends as fast as
            possible.

    Returns:
        Number of requests sent and responses received

    """
    channel = await create_channel_with_credentials(
        options.host, credential_helper
    )

    sent_counter = [0]  # Use list to allow mutation in closure
    received_count = 0
    error_count = 0

    img_gen_func = (
        iter_images
        if rate_limit_min_interval_ms is None
        else lambda max_images, sent_ctr: rate_limited_image_iter(
            rate_limit_min_interval_ms, max_images, sent_ctr
        )
    )

    async with AthenaClient(channel, options) as client:
        generated = img_gen_func(max_test_images, sent_counter)
        results = client.classify_images(generated)

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


async def main() -> int:
    """Run the OAuth classification example."""
    logger = logging.getLogger(__name__)
    load_dotenv()

    # Configuration
    max_test_images = int(os.getenv("TEST_IMAGE_COUNT", str(10_000)))
    min_interval_ms = os.getenv("TEST_MIN_INTERVAL_MS", None)
    if min_interval_ms is not None:
        min_interval_ms = int(min_interval_ms)

    # OAuth credentials from environment
    client_id = os.getenv("OAUTH_CLIENT_ID")
    client_secret = os.getenv("OAUTH_CLIENT_SECRET")
    auth_url = os.getenv(
        "OAUTH_AUTH_URL", "https://crispthinking.auth0.com/oauth/token"
    )
    audience = os.getenv("OAUTH_AUDIENCE", "crisp-athena-dev")

    if not client_id or not client_secret:
        logger.error("OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET must be set")
        return 1

    host = os.getenv("ATHENA_HOST", "localhost")
    logger.info("Connecting to %s", host)

    # Create credential helper
    credential_helper = CredentialHelper(
        client_id=client_id,
        client_secret=client_secret,
        auth_url=auth_url,
        audience=audience,
    )

    # Test token acquisition
    try:
        logger.info("Acquiring OAuth token...")
        token = await credential_helper.get_token()
        logger.info("Successfully acquired token (length: %d)", len(token))
    except Exception:
        logger.exception("Failed to acquire OAuth token")
        return 1

    max_deployment_id_length = 63

    deployment_id = f"smoke-test-{uuid.uuid4()}"
    if len(deployment_id) > max_deployment_id_length:
        deployment_id = deployment_id[:max_deployment_id_length]

    logger.info("Using deployment: %s", deployment_id)

    # Run classification with OAuth authentication
    options = AthenaOptions(
        host=host,
        resize_images=True,
        deployment_id=deployment_id,
        compress_images=True,
        timeout=120.0,  # Maximum duration, not forced timeout
        keepalive_interval=30.0,  # Longer intervals for persistent streams
        affiliate="Crisp",
    )

    sent, received, errors = await run_smoke_test(
        logger, options, credential_helper, max_test_images, min_interval_ms
    )

    if errors > 0:
        logger.warning("Completed Unsuccessfully with %d errors", errors)
        return 1

    if sent == received:
        logger.info("Success: %d requests processed", sent)
        return 0

    logger.warning("Incomplete: %d sent, %d received", sent, received)
    return 1


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    sys.exit(asyncio.run(main()))
