"""Tests for ImageResizer transformer."""

import io
from collections.abc import AsyncIterator

import numpy as np
import pytest
from PIL import Image

from athena_client.client.consts import EXPECTED_HEIGHT, EXPECTED_WIDTH
from athena_client.client.transformers.image_resizer import ImageResizer
from tests.utils.mock_async_iterator import MockAsyncIterator


def create_test_image(width: int, height: int, mode: str = "RGB") -> bytes:
    """Create a test image with specified dimensions."""
    img = Image.new(
        mode, (width, height), color=(255, 0, 0) if mode == "RGB" else 128
    )
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    return img_bytes.getvalue()


@pytest.fixture
def source() -> AsyncIterator[bytes]:
    """Fixture providing an async iterator of test images."""
    test_images = [
        create_test_image(100, 100),  # Smaller than target
        create_test_image(1000, 1000),  # Larger than target
        create_test_image(EXPECTED_WIDTH, EXPECTED_HEIGHT),  # Exact size
    ]
    return MockAsyncIterator(test_images)


@pytest.fixture
def grayscale_image() -> bytes:
    """Create a grayscale test image."""
    return create_test_image(100, 100, mode="L")


@pytest.mark.asyncio
async def test_image_resizer_transform() -> None:
    """Test the ImageResizer transform method with various image sizes."""
    resizer = ImageResizer(MockAsyncIterator([]))

    # Test with smaller image
    small_image = create_test_image(100, 100)
    resized_small = await resizer.transform(small_image)
    small_array = np.frombuffer(resized_small, dtype=np.uint8)
    small_array = small_array.reshape((EXPECTED_HEIGHT, EXPECTED_WIDTH, 3))
    assert small_array.shape == (EXPECTED_HEIGHT, EXPECTED_WIDTH, 3)
    assert small_array.flags["C_CONTIGUOUS"]

    # Test with larger image
    large_image = create_test_image(1000, 1000)
    resized_large = await resizer.transform(large_image)
    large_array = np.frombuffer(resized_large, dtype=np.uint8)
    large_array = large_array.reshape((EXPECTED_HEIGHT, EXPECTED_WIDTH, 3))
    assert large_array.shape == (EXPECTED_HEIGHT, EXPECTED_WIDTH, 3)
    assert large_array.flags["C_CONTIGUOUS"]

    # Test with exactly sized image
    exact_image = create_test_image(EXPECTED_WIDTH, EXPECTED_HEIGHT)
    resized_exact = await resizer.transform(exact_image)
    exact_array = np.frombuffer(resized_exact, dtype=np.uint8)
    exact_array = exact_array.reshape((EXPECTED_HEIGHT, EXPECTED_WIDTH, 3))
    assert exact_array.shape == (EXPECTED_HEIGHT, EXPECTED_WIDTH, 3)
    assert exact_array.flags["C_CONTIGUOUS"]


@pytest.mark.asyncio
async def test_image_resizer_iteration(source: AsyncIterator[bytes]) -> None:
    """Test that ImageResizer properly iterates through source images."""
    resizer = ImageResizer(source)

    # Process all images
    async for resized in resizer:
        array = np.frombuffer(resized, dtype=np.uint8)
        array = array.reshape((EXPECTED_HEIGHT, EXPECTED_WIDTH, 3))
        assert array.shape == (EXPECTED_HEIGHT, EXPECTED_WIDTH, 3)
        assert array.flags["C_CONTIGUOUS"]


@pytest.mark.asyncio
async def test_grayscale_conversion(grayscale_image: bytes) -> None:
    """Test that grayscale images are converted to RGB."""
    resizer = ImageResizer(MockAsyncIterator([]))
    resized = await resizer.transform(grayscale_image)

    array = np.frombuffer(resized, dtype=np.uint8)
    array = array.reshape((EXPECTED_HEIGHT, EXPECTED_WIDTH, 3))
    assert array.shape == (EXPECTED_HEIGHT, EXPECTED_WIDTH, 3)  # Should be RGB
    assert array.flags["C_CONTIGUOUS"]


@pytest.mark.asyncio
async def test_output_format() -> None:
    """Test that the output is valid image bytes in contiguous array format."""
    resizer = ImageResizer(MockAsyncIterator([]))
    test_image = create_test_image(100, 100)

    result = await resizer.transform(test_image)

    # The output should be a contiguous numpy array in bytes form
    array = np.frombuffer(result, dtype=np.uint8)
    array = array.reshape((EXPECTED_HEIGHT, EXPECTED_WIDTH, 3))
    assert array.flags["C_CONTIGUOUS"]
    assert isinstance(result, bytes)
    assert (
        len(result) == EXPECTED_WIDTH * EXPECTED_HEIGHT * 3
    )  # RGB = 3 channels
