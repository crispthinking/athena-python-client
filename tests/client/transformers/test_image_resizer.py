"""Tests for ImageResizer transformer."""

import hashlib
import io
from collections.abc import AsyncIterator

import pytest
from PIL import Image

from athena_client.client.consts import EXPECTED_HEIGHT, EXPECTED_WIDTH
from athena_client.client.models import ImageData
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
def source() -> AsyncIterator[ImageData]:
    """Fixture providing an async iterator of test images."""
    test_images = [
        ImageData(create_test_image(100, 100)),  # Smaller than target
        ImageData(create_test_image(1000, 1000)),  # Larger than target
        ImageData(
            create_test_image(EXPECTED_WIDTH, EXPECTED_HEIGHT)
        ),  # Exact size
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
    small_image = ImageData(create_test_image(100, 100))
    resized_small = await resizer.transform(small_image)
    # Verify output is valid PNG with expected dimensions
    with Image.open(io.BytesIO(resized_small.data)) as img:
        assert img.format == "PNG"
        assert img.size == (EXPECTED_WIDTH, EXPECTED_HEIGHT)
        assert img.mode == "RGB"

    # Test with larger image
    large_image = ImageData(create_test_image(1000, 1000))
    resized_large = await resizer.transform(large_image)
    with Image.open(io.BytesIO(resized_large.data)) as img:
        assert img.format == "PNG"
        assert img.size == (EXPECTED_WIDTH, EXPECTED_HEIGHT)
        assert img.mode == "RGB"

    # Test with exactly sized image
    exact_image = ImageData(create_test_image(EXPECTED_WIDTH, EXPECTED_HEIGHT))
    resized_exact = await resizer.transform(exact_image)
    with Image.open(io.BytesIO(resized_exact.data)) as img:
        assert img.format == "PNG"
        assert img.size == (EXPECTED_WIDTH, EXPECTED_HEIGHT)
        assert img.mode == "RGB"


@pytest.mark.asyncio
async def test_image_resizer_iteration(
    source: AsyncIterator[ImageData],
) -> None:
    """Test that ImageResizer properly iterates through source images."""
    resizer = ImageResizer(source)

    # Process all images
    async for resized in resizer:
        # Verify output is valid PNG image
        with Image.open(io.BytesIO(resized.data)) as img:
            assert img.format == "PNG"
            assert img.size == (EXPECTED_WIDTH, EXPECTED_HEIGHT)
            assert img.mode == "RGB"


@pytest.mark.asyncio
async def test_grayscale_conversion(grayscale_image: bytes) -> None:
    """Test that grayscale images are converted to RGB."""
    resizer = ImageResizer(MockAsyncIterator([]))
    grayscale_data = ImageData(grayscale_image)
    resized = await resizer.transform(grayscale_data)

    # Verify output is valid PNG and converted to RGB
    with Image.open(io.BytesIO(resized.data)) as img:
        assert img.size == (EXPECTED_WIDTH, EXPECTED_HEIGHT)
        assert img.mode == "RGB"  # Should be converted from grayscale


@pytest.mark.asyncio
async def test_output_format() -> None:
    """Test that the output is valid PNG image format."""
    resizer = ImageResizer(MockAsyncIterator([]))
    test_image = ImageData(create_test_image(100, 100))

    result = await resizer.transform(test_image)

    # The output should be valid PNG format
    assert isinstance(result, ImageData)
    assert isinstance(result.data, bytes)

    # Verify it's a valid PNG image
    with Image.open(io.BytesIO(result.data)) as img:
        assert img.format == "PNG"
        assert img.size == (EXPECTED_WIDTH, EXPECTED_HEIGHT)
        assert img.mode == "RGB"


@pytest.mark.asyncio
async def test_image_resizer_recalculates_hashes() -> None:
    """Test that ImageResizer recalculates hashes after resizing.

    Resizing operations should add new hashes to track the transformation
    since image content changed.
    """
    resizer = ImageResizer(MockAsyncIterator([]))
    test_image_bytes = create_test_image(200, 200)  # Larger than expected size
    test_data = ImageData(test_image_bytes)

    # Store original hashes and data for comparison
    original_sha256 = test_data.sha256_hashes.copy()
    original_md5 = test_data.md5_hashes.copy()
    original_data = test_data.data

    # Resize the image
    resized = await resizer.transform(test_data)

    # Note: resized is the same object as test_data (modified in place)
    assert resized is test_data  # Same object reference

    # Verify the data is actually resized (different bytes)
    assert resized.data != original_data
    assert len(resized.data) != len(original_data)

    # Verify hashes are extended (original preserved + new added)
    assert len(resized.sha256_hashes) == len(original_sha256) + 1
    assert len(resized.md5_hashes) == len(original_md5) + 1

    # Verify original hashes are preserved
    assert resized.sha256_hashes[:-1] == original_sha256
    assert resized.md5_hashes[:-1] == original_md5

    # Verify the new hashes match the resized data
    expected_sha256 = hashlib.sha256(resized.data).hexdigest()
    expected_md5 = hashlib.md5(resized.data).hexdigest()
    assert resized.sha256_hashes[-1] == expected_sha256
    assert resized.md5_hashes[-1] == expected_md5
