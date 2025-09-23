#!/usr/bin/env python3
"""Example script demonstrating the classify_single method."""

import asyncio
import logging
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

from resolver_athena_client.client.athena_client import AthenaClient
from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.channel import (
    CredentialHelper,
    create_channel_with_credentials,
)
from resolver_athena_client.client.consts import MAX_DEPLOYMENT_ID_LENGTH
from resolver_athena_client.client.models import ImageData
from tests.utils.image_generation import create_test_image


async def classify_single_image_example(
    logger: logging.Logger,
    options: AthenaOptions,
    credential_helper: CredentialHelper,
    image_path: str | None = None,
) -> bool:
    """Demonstrate single image classification.

    Args:
        logger: Logger instance for output
        options: Configuration options for the Athena client
        credential_helper: OAuth credential helper for authentication
        image_path: Path to image file to classify (optional)

    Returns:
        True if classification was successful, False otherwise

    """
    # Create gRPC channel with credentials
    channel = await create_channel_with_credentials(
        options.host, credential_helper
    )

    async with AthenaClient(channel, options) as client:
        # Load image data
        if image_path and Path(image_path).exists():
            logger.info("Loading image from: %s", image_path)
            image_bytes = Path(image_path).read_bytes()
        else:
            # Create a simple test image if no path provided
            logger.info("Creating synthetic test image")
            image_bytes = create_test_image()

        # Create ImageData object
        image_data = ImageData(image_bytes)
        logger.info(
            "Image loaded: %d bytes, MD5: %s",
            len(image_data.data),
            image_data.md5_hashes[0][:8] + "...",
        )

        try:
            # Classify the single image
            logger.info("Classifying single image...")
            correlation_id = uuid.uuid4().hex[:MAX_DEPLOYMENT_ID_LENGTH]
            logger.info("Correlation ID: %s", correlation_id)
            result = await client.classify_single(
                image_data, correlation_id=correlation_id
            )

            # Process the result
            logger.info("Classification completed successfully!")

            if result.error.code:
                logger.error(
                    "Classification error: %s (%s)",
                    result.error.message,
                    result.error.code,
                )
                if result.error.details:
                    logger.error("Error details: %s", result.error.details)
                return False

            if result.classifications:
                logger.info(
                    "Found %d classifications:", len(result.classifications)
                )
                for i, classification in enumerate(result.classifications, 1):
                    logger.info(
                        "  %d. Label: %s, Weight: %.3f",
                        i,
                        classification.label,
                        classification.weight,
                    )
            else:
                logger.info("No classifications found for this image")

        except Exception:
            logger.exception("Error during single image classification")
            return False
        else:
            return True


async def classify_multiple_single_images_example(
    logger: logging.Logger,
    options: AthenaOptions,
    credential_helper: CredentialHelper,
    num_images: int = 3,
) -> int:
    """Demonstrate classifying multiple images individually.

    This shows how classify_single can be used for multiple images
    when you want individual control over each classification request.

    Args:
        logger: Logger instance for output
        options: Configuration options for the Athena client
        credential_helper: OAuth credential helper for authentication
        num_images: Number of test images to classify

    Returns:
        Number of successfully classified images

    """
    # Create gRPC channel with credentials
    channel = await create_channel_with_credentials(
        options.host, credential_helper
    )

    successful_count = 0

    async with AthenaClient(channel, options) as client:
        logger.info("Classifying %d images individually...", num_images)

        for i in range(num_images):
            try:
                # Create a unique test image for each iteration
                image_bytes = create_test_image(seed=i)
                image_data = ImageData(image_bytes)

                # Classify with auto-generated correlation ID
                result = await client.classify_single(image_data)

                logger.info(
                    "Image %d/%d - Correlation: %s",
                    i + 1,
                    num_images,
                    result.correlation_id[:8] + "...",
                )

                if result.error.code:
                    logger.warning(
                        "Image %d failed: %s", i + 1, result.error.message
                    )
                elif result.classifications:
                    top_classification = max(
                        result.classifications, key=lambda c: c.weight
                    )
                    logger.info(
                        "Image %d - Top result: %s (%.3f)",
                        i + 1,
                        top_classification.label,
                        top_classification.weight,
                    )
                    successful_count += 1
                else:
                    logger.info("Image %d - No classifications", i + 1)
                    successful_count += 1

            except Exception:  # noqa: PERF203
                logger.exception("Failed to classify image %d", i + 1)

    logger.info(
        "Completed: %d/%d images classified successfully",
        successful_count,
        num_images,
    )
    return successful_count


async def main() -> int:
    """Run the classify_single examples."""
    logger = logging.getLogger(__name__)
    load_dotenv()

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

    # Configure client options
    options = AthenaOptions(
        host=host,
        resize_images=True,
        compress_images=True,
        timeout=30.0,  # Shorter timeout for single requests
        affiliate="Crisp",
        deployment_id="single-example-deployment",  # Not used
    )

    try:
        # Example 1: Classify a single image
        logger.info("\n=== Example 1: Single Image Classification ===")
        success = await classify_single_image_example(
            logger,
            options,
            credential_helper,
            image_path=os.getenv("TEST_IMAGE_PATH"),  # Optional image path
        )

        if not success:
            logger.error("Single image classification failed")
            return 1

        # Example 2: Classify multiple images individually
        logger.info("\n=== Example 2: Multiple Individual Classifications ===")
        successful_count = await classify_multiple_single_images_example(
            logger, options, credential_helper, num_images=5
        )

        if successful_count == 0:
            logger.error("No images were successfully classified")
            return 1

        logger.info("\n=== All examples completed successfully! ===")

    except Exception:
        logger.exception("Examples failed")
        return 1
    else:
        return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    sys.exit(asyncio.run(main()))
