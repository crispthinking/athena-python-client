#!/usr/bin/env python3
"""Example script that uses the athena client."""

import asyncio
import io
import logging
import os
import random
from collections.abc import AsyncIterator
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image, ImageDraw

from athena_client.client.athena_client import AthenaClient
from athena_client.client.athena_options import AthenaOptions
from athena_client.client.channel import create_channel

EXAMPLE_IMAGES_DIR = Path(__file__).parent / "example_images"


def create_random_image(width: int = 640, height: int = 480) -> bytes:
    """Create a random test image with random shapes and colors.

    Args:
        width: Width of the test image in pixels
        height: Height of the test image in pixels

    Returns:
        JPEG image bytes

    """
    # Create a new image with random background color
    image = Image.new(
        "RGB",
        (width, height),
        (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
        ),
    )

    draw = ImageDraw.Draw(image)

    # Draw some random shapes
    for _ in range(3):
        # Random coordinates
        x0 = random.randint(0, width - 1)
        y0 = random.randint(0, height - 1)
        x1 = random.randint(0, width - 1)
        y1 = random.randint(0, height - 1)

        # Random color
        color = (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
        )

        draw.rectangle(
            [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)], fill=color
        )

    # Convert to JPEG bytes
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format="JPEG")
    return img_byte_arr.getvalue()


async def iter_images(max_images: int | None = None) -> AsyncIterator[bytes]:
    """Generate random test images.

    Args:
        max_images: Maximum number of images to generate. If None, generates
        infinitely.

    Yields:
        JPEG image bytes with random content

    """
    count = 0
    while max_images is None or count < max_images:
        yield create_random_image()
        count += 1


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
        results = client.classify_images(iter_images(max_test_images))
        logger.info("Classifying images in image iter")
        async for result in results:
            result_msg = f"Get result {result=}"
            logger.info(result_msg)


async def main() -> None:
    """Run examples showing both authenticated and unauthenticated usage."""
    logger = logging.getLogger(__name__)
    load_dotenv()

    # Set maximum number of test images to generate (None for infinite)
    max_test_images = 5

    # Example with authenticated channel
    auth_token = os.getenv("ATHENA_AUTH_TOKEN")
    if auth_token:
        logger.info("Running example with secure authenticated channel...")
        auth_options = AthenaOptions(
            host=os.getenv("ATHENA_HOST", "localhost"),
            resize_images=True,
            deployment_id="argh",
        )
        await run_example(logger, auth_options, auth_token, max_test_images)
    else:
        logger.info(
            "Skipping authenticated example - ATHENA_AUTH_TOKEN not set"
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
