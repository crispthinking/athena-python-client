import logging
import os

import pytest

from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.channel import CredentialHelper
from resolver_athena_client.image_generation import (
    create_random_image_generator,
)
from tests.utils.streaming_classify_utils import (
    classify_images,
    classify_images_break_on_first_result,
)


@pytest.mark.asyncio
@pytest.mark.functional
async def test_streaming_classify(
    athena_options: AthenaOptions, credential_helper: CredentialHelper
) -> None:
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

    assert errors == 0, f"{errors} errors occurred during stream processing"
    assert sent == received, f"Incomplete: {sent} sent, {received} received"


@pytest.mark.asyncio
@pytest.mark.functional
async def test_streaming_classify_with_reopened_stream(
    athena_options: AthenaOptions, credential_helper: CredentialHelper
) -> None:
    logger = logging.getLogger(__name__)

    # Configuration
    max_test_images = int(os.getenv("TEST_IMAGE_COUNT", str(1_000)))
    min_interval_ms = os.getenv("TEST_MIN_INTERVAL_MS", None)
    if min_interval_ms is not None:
        min_interval_ms = int(min_interval_ms)

    image_generator = create_random_image_generator(
        max_test_images, min_interval_ms
    )

    sent, recv, errors = await classify_images_break_on_first_result(
        logger,
        athena_options,
        credential_helper,
        image_generator,
    )

    assert sent > 0, "First stream did not send any images"
    assert recv < sent, (
        "First stream received all results - cannot test reopening"
    )

    if errors > 0:
        msg = f"First stream returned encountered {errors} errors. Cannot "
        "continue."
        raise AssertionError(msg)

    empty_generator = create_random_image_generator(0, None)

    sent2, recv2, errors2 = await classify_images_break_on_first_result(
        logger,
        athena_options,
        credential_helper,
        empty_generator,
    )

    errors += errors2

    assert errors == 0, f"{errors} errors occurred during stream processing"
    assert sent2 == 0
    assert recv2 > 0, "Second stream did not receive any results"
