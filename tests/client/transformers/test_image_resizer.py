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

# Test constants
EXPECTED_HASH_COUNT_AFTER_TRANSFORM = 2  # Original + transformed


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
    # Verify output is raw RGB bytes with expected dimensions
    expected_size = EXPECTED_WIDTH * EXPECTED_HEIGHT * 3
    assert len(resized_small.data) == expected_size
    # Verify it can be converted back to an image
    img = Image.frombytes(
        "RGB", (EXPECTED_WIDTH, EXPECTED_HEIGHT), resized_small.data
    )
    assert img.size == (EXPECTED_WIDTH, EXPECTED_HEIGHT)
    assert img.mode == "RGB"

    # Test with larger image
    large_image = ImageData(create_test_image(1000, 1000))
    resized_large = await resizer.transform(large_image)
    assert len(resized_large.data) == expected_size
    img = Image.frombytes(
        "RGB", (EXPECTED_WIDTH, EXPECTED_HEIGHT), resized_large.data
    )
    assert img.size == (EXPECTED_WIDTH, EXPECTED_HEIGHT)
    assert img.mode == "RGB"

    # Test with exactly sized image
    exact_image = ImageData(create_test_image(EXPECTED_WIDTH, EXPECTED_HEIGHT))
    resized_exact = await resizer.transform(exact_image)
    assert len(resized_exact.data) == expected_size
    img = Image.frombytes(
        "RGB", (EXPECTED_WIDTH, EXPECTED_HEIGHT), resized_exact.data
    )
    assert img.size == (EXPECTED_WIDTH, EXPECTED_HEIGHT)
    assert img.mode == "RGB"


@pytest.mark.asyncio
async def test_image_resizer_iteration(
    source: AsyncIterator[ImageData],
) -> None:
    """Test that ImageResizer properly iterates through source images."""
    resizer = ImageResizer(source)

    # Process all images
    expected_size = EXPECTED_WIDTH * EXPECTED_HEIGHT * 3
    async for resized in resizer:
        # Verify output is raw RGB bytes
        assert len(resized.data) == expected_size
        # Verify it can be converted back to an image
        img = Image.frombytes(
            "RGB", (EXPECTED_WIDTH, EXPECTED_HEIGHT), resized.data
        )
        assert img.size == (EXPECTED_WIDTH, EXPECTED_HEIGHT)
        assert img.mode == "RGB"


@pytest.mark.asyncio
async def test_grayscale_conversion(grayscale_image: bytes) -> None:
    """Test that grayscale images are converted to RGB."""
    resizer = ImageResizer(MockAsyncIterator([]))
    grayscale_data = ImageData(grayscale_image)
    resized = await resizer.transform(grayscale_data)

    # Verify output is raw RGB bytes and converted from grayscale
    expected_size = EXPECTED_WIDTH * EXPECTED_HEIGHT * 3
    assert len(resized.data) == expected_size
    # Verify it can be converted back to an image
    img = Image.frombytes(
        "RGB", (EXPECTED_WIDTH, EXPECTED_HEIGHT), resized.data
    )
    assert img.size == (EXPECTED_WIDTH, EXPECTED_HEIGHT)
    assert img.mode == "RGB"  # Should be converted from grayscale


@pytest.mark.asyncio
async def test_output_format() -> None:
    """Test that the output is valid raw RGB format."""
    resizer = ImageResizer(MockAsyncIterator([]))
    test_image = ImageData(create_test_image(100, 100))

    result = await resizer.transform(test_image)

    # The output should be raw RGB bytes
    assert isinstance(result, ImageData)
    assert isinstance(result.data, bytes)
    expected_size = EXPECTED_WIDTH * EXPECTED_HEIGHT * 3
    assert len(result.data) == expected_size

    # Verify it's valid raw RGB data
    img = Image.frombytes("RGB", (EXPECTED_WIDTH, EXPECTED_HEIGHT), result.data)
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


@pytest.mark.asyncio
async def test_raw_rgb_fast_path() -> None:
    """Test that raw RGB arrays of correct size are passed through unchanged."""
    resizer = ImageResizer(MockAsyncIterator([]))

    # Create raw RGB data of expected size
    expected_size = EXPECTED_WIDTH * EXPECTED_HEIGHT * 3
    raw_rgb_data = b"\x00" * expected_size  # Black image

    test_image = ImageData(raw_rgb_data)
    original_data = test_image.data

    result = await resizer.transform(test_image)

    # Should be unchanged (fast path)
    assert result.data is original_data  # Same object reference
    assert len(result.data) == expected_size

    # Verify it's still valid RGB data
    img = Image.frombytes("RGB", (EXPECTED_WIDTH, EXPECTED_HEIGHT), result.data)
    assert img.size == (EXPECTED_WIDTH, EXPECTED_HEIGHT)
    assert img.mode == "RGB"


@pytest.mark.asyncio
async def test_160x120_png_resize() -> None:
    """Test that 160x120 PNG data gets properly resized."""
    resizer = ImageResizer(MockAsyncIterator([]))

    # Create 160x120 PNG data (same as create_image.py)
    width, height = 160, 120
    img = Image.new("RGB", (width, height), color=(255, 0, 0))

    # Convert to PNG bytes
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    png_data = buffer.getvalue()

    test_image = ImageData(png_data)
    result = await resizer.transform(test_image)

    # Should be resized to expected dimensions
    expected_size = EXPECTED_WIDTH * EXPECTED_HEIGHT * 3
    assert len(result.data) == expected_size

    # Verify it can be converted back to an image with correct dimensions
    resized_img = Image.frombytes(
        "RGB", (EXPECTED_WIDTH, EXPECTED_HEIGHT), result.data
    )
    assert resized_img.size == (EXPECTED_WIDTH, EXPECTED_HEIGHT)
    assert resized_img.mode == "RGB"

    # Verify hashes were recalculated (transformation occurred)
    assert len(result.sha256_hashes) == EXPECTED_HASH_COUNT_AFTER_TRANSFORM
    assert len(result.md5_hashes) == EXPECTED_HASH_COUNT_AFTER_TRANSFORM
