#!/usr/bin/env python3
"""Example script demonstrating OAuth credential helper usage."""

import asyncio
import logging
import os
import sys
import time
import uuid

from create_image import iter_images
from dotenv import load_dotenv

from resolver_athena_client.client.athena_client import AthenaClient
from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.channel import (
    CredentialHelper,
    create_channel_with_credentials,
)
from resolver_athena_client.client.deployment_selector import DeploymentSelector
from resolver_athena_client.client.utils import (
    get_output_error_summary,
    has_output_errors,
    process_classification_outputs,
)


async def run_oauth_example(
    logger: logging.Logger,
    options: AthenaOptions,
    credential_helper: CredentialHelper,
    max_test_images: int | None = None,
) -> tuple[int, int]:
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

    async with AthenaClient(channel, options) as client:
        results = client.classify_images(
            iter_images(max_test_images, sent_counter)
        )

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

                # Check for output errors and handle them
                if has_output_errors(result):
                    error_summary = get_output_error_summary(result)
                    logger.warning(
                        "Received %d outputs with errors: %s",
                        sum(error_summary.values()),
                        error_summary,
                    )

                # Process outputs, logging errors but continuing with
                # successful ones
                successful_outputs = process_classification_outputs(
                    result, raise_on_error=False, log_errors=True
                )

                for output in successful_outputs:
                    classifications = {
                        c.label: round(c.weight, 3)
                        for c in output.classifications
                    }
                    logger.debug(
                        "Result [%s]: %s",
                        output.correlation_id[:8],
                        classifications,
                    )

        except Exception:
            logger.exception("Error during classification")
            if received_count == 0:
                raise
        finally:
            duration = time.time() - start_time
            if received_count > 0:
                avg_rate = received_count / duration if duration > 0 else 0
                logger.info(
                    "Completed: sent=%d received=%d in %.1fs (%.1f/sec)",
                    sent_counter[0],
                    received_count,
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

    return (sent_counter[0], received_count)


async def main() -> int:
    """Run the OAuth classification example."""
    logger = logging.getLogger(__name__)
    load_dotenv()

    # Configuration
    max_test_images = 10_000

    # OAuth credentials from environment
    client_id = os.getenv("OAUTH_CLIENT_ID")
    client_secret = os.getenv("OAUTH_CLIENT_SECRET")
    auth_url = os.getenv(
        "OAUTH_AUTH_URL", "https://crispthinking.auth0.com/oauth/token"
    )
    audience = os.getenv("OAUTH_AUDIENCE", "crisp-athena-live")

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

    # Get available deployment
    channel = await create_channel_with_credentials(host, credential_helper)
    async with DeploymentSelector(channel) as deployment_selector:
        deployments = await deployment_selector.list_deployments()

    if deployments.deployments:
        deployment_id = deployments.deployments[0].deployment_id
    else:
        deployment_id = uuid.uuid4().hex

    logger.info("Using deployment: %s", deployment_id)

    # Run classification with OAuth authentication
    options = AthenaOptions(
        host=host,
        resize_images=True,
        deployment_id=deployment_id,
        compress_images=True,
        timeout=120.0,  # Maximum duration, not forced timeout
        keepalive_interval=30.0,  # Longer intervals for persistent streams
        affiliate="crisp",
    )

    sent, received = await run_oauth_example(
        logger, options, credential_helper, max_test_images
    )

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
