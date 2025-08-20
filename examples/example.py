#!/usr/bin/env python3
"""Example script that uses the athena client."""

import asyncio
import logging
import os
import sys
import time

from create_image import iter_images
from dotenv import load_dotenv

from athena_client.client.athena_client import AthenaClient
from athena_client.client.athena_options import AthenaOptions
from athena_client.client.channel import create_channel
from athena_client.client.deployment_selector import DeploymentSelector


async def run_example(
    logger: logging.Logger,
    options: AthenaOptions,
    auth_token: str,
    max_test_images: int | None = None,
) -> None:
    """Run an example classification with the given options.

    Args:
        logger: Logger instance for output
        options: Configuration options for the Athena client
        auth_token: Authentication token for the API
        max_test_images: Maximum number of test images to generate
            (None for infinite)

    """
    channel = create_channel(options.host, auth_token)

    async with AthenaClient(channel, options) as client:
        # Start image classification
        results = client.classify_images(iter_images(max_test_images))
        logger.info("Starting classification...")

        # Initialize rate tracking
        start_time = time.time()
        response_count = 0

        try:
            async for result in results:
                response_count += 1
                current_time = time.time()
                elapsed = current_time - start_time

                if response_count % 10 == 0:
                    rate = response_count / elapsed
                    logger.info(
                        "Processed %d responses (%.1f/sec)",
                        response_count,
                        rate,
                    )

                logger.debug("Got result: %s", result)
        except Exception:
            logger.exception("Error during classification")
            if response_count == 0:
                # Re-raise if we didn't process any responses
                raise
        finally:
            # Calculate final statistics after loop completes
            if response_count > 0:
                duration = time.time() - start_time
                avg_rate = response_count / duration
                logger.info(
                    "\nFinal: %d responses in %.1f seconds (%.1f/sec)",
                    response_count,
                    duration,
                    avg_rate,
                )


async def main() -> int:
    """Run examples showing both authenticated and unauthenticated usage."""
    logger = logging.getLogger(__name__)
    load_dotenv()

    # Set maximum number of test images to generate (None for infinite)
    max_test_images = None

    # Example with authenticated channel
    auth_token = os.getenv("ATHENA_AUTH_TOKEN")
    if not auth_token:
        logger.error("ATHENA_AUTH_TOKEN not set.")
        return 1

    logger.info("Running example with secure authenticated channel")
    host = os.getenv("ATHENA_HOST", "localhost")
    channel = create_channel(host, auth_token)

    # Get the first available deployment using context manager
    async with DeploymentSelector(channel) as deployment_selector:
        deployments = await deployment_selector.list_deployments()

    if not deployments.deployments:
        logger.error("No deployments available")
        return 1

    deployment_id = deployments.deployments[0].deployment_id
    logger.info("Using deployment: %s", deployment_id)

    athena_options = AthenaOptions(
        host=host,
        resize_images=True,
        deployment_id=deployment_id,
        compress_images=True,
    )
    await run_example(logger, athena_options, auth_token, max_test_images)

    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s.%(msecs)03d %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    sys.exit(asyncio.run(main()))
