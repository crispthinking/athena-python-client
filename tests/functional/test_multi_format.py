import logging

import pytest

from resolver_athena_client.client.athena_client import AthenaClient
from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.channel import (
    CredentialHelper,
    create_channel_with_credentials,
)
from resolver_athena_client.client.models import ImageData
from resolver_athena_client.generated.athena.models_pb2 import ImageFormat
from tests.utils.image_generation import (
    create_random_image_generator_uint8,
)
from tests.utils.streaming_classify_utils import (
    classify_images,
)


@pytest.mark.asyncio
@pytest.mark.functional
async def test_classify_single_multi_format(
    athena_options: AthenaOptions,
    credential_helper: CredentialHelper,
    valid_formatted_image: bytes,
) -> None:
    # Create gRPC channel with credentials
    channel = await create_channel_with_credentials(
        athena_options.host, credential_helper
    )

    async with AthenaClient(channel, athena_options) as client:
        image_data = ImageData(valid_formatted_image)

        # Classify with auto-generated correlation ID
        result = await client.classify_single(image_data)

        if result.error.code:
            msg = f"Image Result Error: {result.error.message}"
            pytest.fail(msg)


@pytest.mark.asyncio
@pytest.mark.functional
async def test_classify_streaming_legacy_brg_format(
    athena_options: AthenaOptions,
    credential_helper: CredentialHelper,
) -> None:
    logger = logging.getLogger(__name__)

    max_test_images = 50  # small, as this is just a format test

    image_generator = create_random_image_generator_uint8(
        max_test_images, ImageFormat.IMAGE_FORMAT_RAW_UINT8_BRG
    )

    athena_options.max_batch_size = 5

    sent, received, errors = await classify_images(
        logger,
        athena_options,
        credential_helper,
        max_test_images,
        image_generator,
    )

    assert errors == 0, f"{errors} errors occurred during stream processing"
    assert sent == received, f"Incomplete: {sent} sent, {received} received"
