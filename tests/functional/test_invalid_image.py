import logging
from collections.abc import AsyncIterator

import pytest

from resolver_athena_client.client.athena_client import AthenaClient
from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.channel import (
    CredentialHelper,
    create_channel_with_credentials,
)
from resolver_athena_client.client.consts import EXPECTED_HEIGHT, EXPECTED_WIDTH
from resolver_athena_client.client.exceptions import AthenaError
from resolver_athena_client.client.models import ImageData
from tests.utils.image_generation import create_test_image
from tests.utils.streaming_classify_utils import classify_images


@pytest.mark.asyncio
@pytest.mark.functional
async def test_classify_single_invalid_image(
    athena_options: AthenaOptions, credential_helper: CredentialHelper
) -> None:
    """Functional test for ClassifySingle endpoint and API methods.

    This test creates a unique test image for each iteration and classifies it.
    The test runs multiple iterations to ensure consistent behavior.
    """

    # Create gRPC channel with credentials
    channel = await create_channel_with_credentials(
        athena_options.host, credential_helper
    )

    async with AthenaClient(channel, athena_options) as client:
        try:
            # Create a unique test image for each iteration
            image_bytes = b"this is not a valid image file"
            image_data = ImageData(image_bytes)

            with pytest.raises(
                ValueError, match="Failed to decode image data for resizing"
            ) as e:
                _ = await client.classify_single(image_data)

        except Exception as e:
            msg = "Unexpected exception during invalid image test"
            raise AssertionError(msg) from e


@pytest.mark.asyncio
@pytest.mark.functional
@pytest.mark.parametrize(
    ("image_width", "image_height"),
    [
        pytest.param(500, 500, id="too-big-both-dimensions"),
        pytest.param(50, 50, id="too-small-both-dimensions"),
        pytest.param(500, EXPECTED_HEIGHT, id="too-big-width"),
        pytest.param(EXPECTED_WIDTH, 500, id="too-big-height"),
        pytest.param(50, EXPECTED_HEIGHT, id="too-small-width"),
        pytest.param(EXPECTED_WIDTH, 50, id="too-small-height"),
    ],
)
async def test_classify_single_invalid_size_image(
    athena_options: AthenaOptions,
    credential_helper: CredentialHelper,
    image_width: int,
    image_height: int,
) -> None:
    """Functional test for ClassifySingle endpoint and API methods.

    This test creates a unique test image for each iteration and classifies it.
    The test runs multiple iterations to ensure consistent behavior.
    """

    # Create gRPC channel with credentials
    channel = await create_channel_with_credentials(
        athena_options.host, credential_helper
    )

    athena_options.resize_images = False

    async with AthenaClient(channel, athena_options) as client:
        try:
            # Create a unique test image for each iteration
            image_bytes = create_test_image(
                width=image_width, height=image_height
            )
            image_data = ImageData(image_bytes)

            with pytest.raises(AthenaError) as e:
                _ = await client.classify_single(image_data)

            assert "Image Classification Error" in str(e.value)

        except Exception as e:
            msg = "Unexpected exception during invalid image test"
            raise AssertionError(msg) from e


@pytest.mark.asyncio
@pytest.mark.functional
async def test_classify_streaming_one_bad_image(
    athena_options: AthenaOptions, credential_helper: CredentialHelper
) -> None:
    """Functional test for ClassifyStreaming with one invalid image in the
    stream."""
    images: list[bytes] = []
    images_to_generate = 32
    for i in range(images_to_generate):
        if i == images_to_generate // 2:
            images.append(
                create_test_image(
                    width=50, height=50, seed=i, img_format="RAW_UINT8"
                )
            )
        else:
            images.append(
                create_test_image(
                    width=EXPECTED_WIDTH,
                    height=EXPECTED_HEIGHT,
                    seed=i,
                    img_format="RAW_UINT8",
                )
            )

    async def generate_images() -> AsyncIterator[ImageData]:
        for img in images:
            yield ImageData(img)

    athena_options.resize_images = False

    logger = logging.getLogger(__name__)

    sent, recv, errors = await classify_images(
        logger,
        athena_options,
        credential_helper,
        images_to_generate,
        generate_images(),
    )

    assert sent == images_to_generate, (
        f"Sent {sent}, expected {images_to_generate}"
    )
    assert recv == images_to_generate, (
        f"Received {recv}, expected {images_to_generate}"
    )
    assert errors == 1, f"Expected 1 error, got {errors}"
