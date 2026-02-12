"""Test core transformation functions."""

import cv2 as cv
import numpy as np
import pytest

from resolver_athena_client.client.consts import (
    EXPECTED_HEIGHT,
    EXPECTED_WIDTH,
)
from resolver_athena_client.client.models import ImageData
from resolver_athena_client.client.transformers.core import (
    compress_image,
    resize_image,
)


def create_test_image(
    width: int = 100, height: int = 100, mode: str = "RGB"
) -> bytes:
    """Create a test image with specified dimensions using OpenCV."""
    # Map mode to OpenCV color shape
    if mode == "RGB":
        color = (255, 0, 0)  # Red in RGB
        img = np.full((height, width, 3), color, dtype=np.uint8)
    elif mode == "L":
        color = 76  # Red in grayscale
        img = np.full((height, width), color, dtype=np.uint8)
    else:
        err = f"Unsupported mode: {mode}"
        raise ValueError(err)

    success, buf = cv.imencode(".png", img)
    if not success:
        err = "Failed to encode image to PNG"
        raise RuntimeError(err)

    return buf.tobytes()


@pytest.mark.asyncio
async def test_resize_image_basic() -> None:
    """Test basic image resizing functionality."""
    # Create a test image that needs resizing
    test_image_bytes = create_test_image(200, 150)
    image_data = ImageData(test_image_bytes)

    original_hash_count = len(image_data.md5_hashes)

    # Resize the image
    result = await resize_image(image_data)

    # Should be the same object
    assert result is image_data

    # Should have added a new hash since transformation occurred
    assert len(image_data.md5_hashes) == original_hash_count + 1

    # Data should be different (resized)
    assert image_data.data != test_image_bytes


@pytest.mark.asyncio
async def test_resize_image_already_correct_size() -> None:
    """Test resizing when image is already correct size but needs conversion."""
    # Create image with expected dimensions (but still PNG format)
    test_image_bytes = create_test_image(EXPECTED_WIDTH, EXPECTED_HEIGHT)
    image_data = ImageData(test_image_bytes)

    original_hash_count = len(image_data.md5_hashes)

    # Resize the image
    result = await resize_image(image_data)

    # Should be the same object
    assert result is image_data

    # Should have added new hash since format conversion occurred
    assert len(image_data.md5_hashes) == original_hash_count + 1

    # Data should be different (converted to raw RGB)
    assert image_data.data != test_image_bytes


@pytest.mark.asyncio
async def test_resize_image_grayscale_conversion() -> None:
    """Test resizing with grayscale to RGB conversion."""
    # Create a grayscale test image
    test_image_bytes = create_test_image(100, 100, mode="L")
    image_data = ImageData(test_image_bytes)

    original_hash_count = len(image_data.md5_hashes)

    # Resize the image
    result = await resize_image(image_data)

    # Should be the same object
    assert result is image_data

    # Should have added a new hash since transformation occurred
    assert len(image_data.md5_hashes) == original_hash_count + 1

    # Data should be different (converted and resized)
    assert image_data.data != test_image_bytes


@pytest.mark.asyncio
async def test_resize_image_raw_rgb_fast_path() -> None:
    """Test the fast path for raw RGB data of correct size."""
    # Create raw RGB data of expected size
    expected_size = EXPECTED_WIDTH * EXPECTED_HEIGHT * 3
    raw_rgb_data = b"\x00" * expected_size
    image_data = ImageData(raw_rgb_data)

    original_hash_count = len(image_data.md5_hashes)
    original_data = image_data.data

    # Resize the image
    result = await resize_image(image_data)

    # Should be the same object
    assert result is image_data

    # Should not have added new hash (fast path, no transformation)
    assert len(image_data.md5_hashes) == original_hash_count

    # Data should be unchanged
    assert image_data.data == original_data


def test_compress_image_basic() -> None:
    """Test basic image compression functionality."""
    # Create test image data
    test_data = b"This is some test image data that should be compressed"
    image_data = ImageData(test_data)

    original_hash_count = len(image_data.md5_hashes)

    # Compress the image
    result = compress_image(image_data)

    # Should be the same object
    assert result is image_data

    # Should not have added new hash (compression preserves hashes)
    assert len(image_data.md5_hashes) == original_hash_count

    # Data should be different (compressed)
    assert image_data.data != test_data
    assert len(image_data.data) < len(test_data)  # Should be smaller


def test_compress_image_empty_data() -> None:
    """Test compression with empty data."""
    image_data = ImageData(b"")

    original_hash_count = len(image_data.md5_hashes)

    # Compress the image
    result = compress_image(image_data)

    # Should be the same object
    assert result is image_data

    # Should not have added new hash
    assert len(image_data.md5_hashes) == original_hash_count

    # Data should be compressed (but still small)
    assert (
        len(image_data.data) > 0
    )  # Brotli adds some overhead even for empty data


def test_compress_image_preserves_hashes() -> None:
    """Test that compression preserves the original hash list."""
    # Create image data and add some transformation hashes
    image_data = ImageData(b"test data")
    image_data.add_transformation_hashes()  # Simulate a previous transformation

    original_hashes = image_data.md5_hashes.copy()

    # Compress the image
    _ = compress_image(image_data)

    # Hashes should be unchanged
    assert image_data.md5_hashes == original_hashes


@pytest.mark.asyncio
async def test_combined_transformations() -> None:
    """Test using both resize and compress transformations together."""
    # Create a test image that needs resizing
    test_image_bytes = create_test_image(200, 150)
    image_data = ImageData(test_image_bytes)

    original_data = image_data.data
    original_hash_count = len(image_data.md5_hashes)

    # Apply resize transformation
    _ = await resize_image(image_data)

    # Should have new hash from resizing
    assert len(image_data.md5_hashes) == original_hash_count + 1
    resized_data = image_data.data
    assert resized_data != original_data

    # Apply compression transformation
    _ = compress_image(image_data)

    # Should still have the same number of hashes (compression preserves)
    assert len(image_data.md5_hashes) == original_hash_count + 1
    compressed_data = image_data.data
    assert compressed_data != resized_data
    assert compressed_data != original_data


@pytest.mark.asyncio
async def test_transformations_modify_in_place() -> None:
    """Test that transformations modify the ImageData object in-place."""
    test_image_bytes = create_test_image(100, 100)
    image_data = ImageData(test_image_bytes)

    original_id = id(image_data)

    # Apply transformations
    result1 = await resize_image(image_data)
    result2 = compress_image(image_data)

    # All results should be the same object
    assert id(result1) == original_id
    assert id(result2) == original_id
    assert result1 is image_data
    assert result2 is image_data
