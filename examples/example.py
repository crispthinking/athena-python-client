#!/usr/bin/env python3
"""Example script that uses the athena client."""

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from pathlib import Path

import anyio

from athena_client.client.athena_client import AthenaClient
from athena_client.client.athena_options import AthenaOptions
from athena_client.client.channel import create_channel

EXAMPLE_IMAGES_DIR = Path(__file__).parent / "example_images"


async def iter_images() -> AsyncIterator[bytes]:
    """Asynchronously yield image bytes from the example_images directory."""
    for entry in EXAMPLE_IMAGES_DIR.iterdir():
        if entry.is_file():
            async with await anyio.open_file(entry, "rb") as f:
                yield await f.read()


async def run_example(
    logger: logging.Logger,
    options: AthenaOptions,
    auth_token: str,
) -> None:
    """Run an example classification with the given options."""
    channel = create_channel(options.host, auth_token)

    async with AthenaClient(channel, options) as client:
        results = client.classify_images(iter_images())
        async for result in results:
            logger.info(result)


async def main() -> None:
    """Run examples showing both authenticated and unauthenticated usage."""
    logger = logging.getLogger(__name__)

    # Example with authenticated channel
    auth_token = os.getenv("ATHENA_AUTH_TOKEN")
    if auth_token:
        logger.info("Running example with secure authenticated channel...")
        auth_options = AthenaOptions(
            host=os.getenv("ATHENA_HOST", "localhost"),
            resize_images=True,
            deployment_id="my-deployment",
        )
        await run_example(logger, auth_options, auth_token)
    else:
        logger.info(
            "Skipping authenticated example - ATHENA_AUTH_TOKEN not set"
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
