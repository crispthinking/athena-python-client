import logging
import os

import pytest

from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.channel import CredentialHelper
from tests.utils.image_generation import create_random_image_generator
from tests.utils.streaming_classify_utils import (
    classify_images,
)


@pytest.mark.asyncio
@pytest.mark.functional
async def test_streaming_classify(
    athena_options: AthenaOptions, credential_helper: CredentialHelper
) -> int:
    """Run streaming classify functional test.

    Environment variables are read from .env file if present, or from the
    environment.

    Required environment variables:
        - OAUTH_CLIENT_ID: OAuth client ID
        - OAUTH_CLIENT_SECRET: OAuth client secret

    Optional environment variables:
        - ATHENA_HOST: Athena service host (default: localhost)
        - OAUTH_AUTH_URL: OAuth token URL
        (default: https://crispthinking.auth0.com/oauth/token)
        - OAUTH_AUDIENCE: OAuth audience (default: crisp-athena-live)
        - TEST_IMAGE_COUNT: Number of test images to classify (default: 5000)
        - TEST_MIN_INTERVAL: Minimum interval in milliseconds between sending
          images (default: None, send as fast as possible)
    """
    logger = logging.getLogger(__name__)

    # Configuration
    max_test_images = int(os.getenv("TEST_IMAGE_COUNT", str(5_000)))
    min_interval_ms = os.getenv("TEST_MIN_INTERVAL_MS", None)
    if min_interval_ms is not None:
        min_interval_ms = int(min_interval_ms)

    image_generator = create_random_image_generator(
        max_test_images, min_interval_ms
    )

    sent, received, errors = await classify_images(
        logger,
        athena_options,
        credential_helper,
        max_test_images,
        image_generator,
    )

    if errors > 0:
        msg = f"Completed with {errors} errors"
        raise AssertionError(msg)

    if sent == received:
        return 0

    msg = f"Incomplete: {sent} sent, {received} received"
    raise AssertionError(msg)
