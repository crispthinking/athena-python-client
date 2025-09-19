import logging
from collections.abc import AsyncIterator

import pytest
from PIL import UnidentifiedImageError

from resolver_athena_client.client.athena_client import AthenaClient
from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.channel import (
    CredentialHelper,
    create_channel_with_credentials,
)
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

            with pytest.raises(UnidentifiedImageError) as e:
                await client.classify_single(image_data)

            expected_msg = "cannot identify image file"
            assert expected_msg in str(e.value)

        except Exception as e:
            msg = "Unexpected exception during invalid image test"
            raise AssertionError(msg) from e


@pytest.mark.asyncio
@pytest.mark.functional
@pytest.mark.parametrize(
    ("image_width", "image_height"),
    [
        (500, 500),  # too big both dimensions
        (50, 50),  # too small both dimensions
        (500, 448),  # too big width
        (448, 500),  # too big height
        (50, 448),  # too small width
        (448, 50),  # too small height
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
                await client.classify_single(image_data)

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
    images = []
    images_to_generate = 32
    for i in range(images_to_generate):
        if i == images_to_generate // 2:
            images.append(create_test_image(width=500, height=500, seed=i))
        else:
            images.append(create_test_image(width=448, height=448, seed=i))

    async def generate_images() -> AsyncIterator[ImageData]:
        for img in images:
            yield ImageData(img)

    logger = logging.getLogger(__name__)

    athena_options.resize_images = False  # set to false to trigger error

    sent, recv, errors = await classify_images(
        logger,
        athena_options,
        credential_helper,
        images_to_generate,
        generate_images(),
    )

    assert sent == images_to_generate
    assert recv == images_to_generate - 1
    assert errors == 1
