"""Functional test for classifying images with specific color channels."""

import numpy as np
import pytest

from resolver_athena_client.client.athena_client import AthenaClient
from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.channel import (
    CredentialHelper,
    create_channel_with_credentials,
)
from resolver_athena_client.client.consts import EXPECTED_HEIGHT, EXPECTED_WIDTH
from resolver_athena_client.client.models import ImageData


def create_color_channel_image(
    channel: str, width: int = EXPECTED_WIDTH, height: int = EXPECTED_HEIGHT
) -> bytes:
    """Create a raw BGR image with only one channel set to 255.

    Args:
        channel: Color channel to set - 'red', 'green', or 'blue'
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        Raw BGR uint8 image bytes

    """
    # Create BGR image (3 channels)
    img = np.zeros((height, width, 3), dtype=np.uint8)

    # Set the specified channel to 255
    if channel == "red":
        img[:, :, 2] = 255  # Red is channel 2 in BGR
    elif channel == "green":
        img[:, :, 1] = 255  # Green is channel 1 in BGR
    elif channel == "blue":
        img[:, :, 0] = 255  # Blue is channel 0 in BGR
    else:
        msg = f"Invalid channel: {channel}. Must be 'red', 'green', or 'blue'"
        raise ValueError(msg)

    return img.tobytes()


@pytest.mark.asyncio
@pytest.mark.functional
async def test_classify_color_channels(
    athena_options: AthenaOptions, credential_helper: CredentialHelper
) -> None:
    """Test classification of three images with distinct color channels.

    Creates and classifies three 448x448x3 images:
    - Red image: R=255, G=0, B=0
    - Green image: R=0, G=255, B=0
    - Blue image: R=0, G=0, B=255
    """
    # Create gRPC channel with credentials
    channel = await create_channel_with_credentials(
        athena_options.host, credential_helper
    )

    async with AthenaClient(channel, athena_options) as client:
        # Test red channel image
        red_image_bytes = create_color_channel_image("red")
        red_image_data = ImageData(red_image_bytes)

        red_result = await client.classify_single(red_image_data)

        if red_result.error.code:
            msg = f"Red image classification error: {red_result.error.message}"
            pytest.fail(msg)

        assert len(red_result.classifications) > 0, "No classifications for red image"

        # Test green channel image
        green_image_bytes = create_color_channel_image("green")
        green_image_data = ImageData(green_image_bytes)

        green_result = await client.classify_single(green_image_data)

        if green_result.error.code:
            msg = (
                f"Green image classification error: {green_result.error.message}"
            )
            pytest.fail(msg)

        assert (
            len(green_result.classifications) > 0
        ), "No classifications for green image"

        # Test blue channel image
        blue_image_bytes = create_color_channel_image("blue")
        blue_image_data = ImageData(blue_image_bytes)

        blue_result = await client.classify_single(blue_image_data)

        if blue_result.error.code:
            msg = f"Blue image classification error: {blue_result.error.message}"
            pytest.fail(msg)

        assert (
            len(blue_result.classifications) > 0
        ), "No classifications for blue image"

        # Verify all three images were successfully classified
        assert red_result.classifications, "Red image has no classifications"
        assert green_result.classifications, "Green image has no classifications"
        assert blue_result.classifications, "Blue image has no classifications"
