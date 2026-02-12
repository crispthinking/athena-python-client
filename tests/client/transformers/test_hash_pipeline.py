"""Tests for hash list behavior throughout the transformation pipeline."""

import hashlib

import cv2 as cv
import numpy as np
import pytest

from resolver_athena_client.client.consts import EXPECTED_HEIGHT, EXPECTED_WIDTH
from resolver_athena_client.client.models import ImageData
from resolver_athena_client.client.transformers.core import (
    compress_image,
    resize_image,
)

# Constants for hash count assertions
ORIGINAL_HASH_COUNT = 1
AFTER_RESIZE_COUNT = 2
AFTER_SECOND_RESIZE_COUNT = 3


def create_test_png_image(width: int = 200, height: int = 200) -> bytes:
    """Create a test PNG image with specified dimensions."""

    # Create a red RGB image using numpy
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (255, 0, 0)  # Red color

    # Encode image as PNG to memory
    success, buffer = cv.imencode(".png", img)
    if not success:
        err = "Failed to encode image as PNG"
        raise RuntimeError(err)
    return buffer.tobytes()


@pytest.mark.asyncio
async def test_hash_pipeline_complete_flow() -> None:
    """Test hash list behavior through complete transformation pipeline."""
    # Create initial image data
    original_png_bytes = create_test_png_image(300, 300)  # Larger than expected
    original_image = ImageData(original_png_bytes)

    # Verify initial state
    assert len(original_image.sha256_hashes) == 1
    assert len(original_image.md5_hashes) == 1
    original_sha256 = original_image.sha256_hashes[0]
    original_md5 = original_image.md5_hashes[0]

    # Step 1: Resize the image (should add new hashes)
    resized_image = await resize_image(original_image)

    # Verify resize added new hashes
    assert len(resized_image.sha256_hashes) == AFTER_RESIZE_COUNT
    assert len(resized_image.md5_hashes) == AFTER_RESIZE_COUNT
    assert (
        resized_image.sha256_hashes[0] == original_sha256
    )  # Original preserved
    assert resized_image.md5_hashes[0] == original_md5  # Original preserved

    # New hash should match the resized data (raw RGB bytes)
    expected_resize_sha256 = hashlib.sha256(resized_image.data).hexdigest()
    expected_resize_md5 = hashlib.md5(resized_image.data).hexdigest()
    assert resized_image.sha256_hashes[1] == expected_resize_sha256
    assert resized_image.md5_hashes[1] == expected_resize_md5

    # Store data before compression for comparison
    raw_data_before_compression = resized_image.data
    raw_data_size_before = len(resized_image.data)

    # Step 2: Compress with Brotli (should preserve all hashes)
    compressed_image = compress_image(resized_image)

    # Note: compressed_image is the same object as resized_image (modified)
    assert compressed_image is resized_image  # Same object reference

    # Verify compression preserved all existing hashes
    assert (
        len(compressed_image.sha256_hashes) == AFTER_RESIZE_COUNT
    )  # No new hashes added
    assert (
        len(compressed_image.md5_hashes) == AFTER_RESIZE_COUNT
    )  # No new hashes added

    # Verify data was actually compressed
    assert compressed_image.data != raw_data_before_compression
    assert len(compressed_image.data) < raw_data_size_before

    # Final verification: Hash history tells the story
    assert compressed_image.sha256_hashes[0] == original_sha256  # Original PNG
    assert (
        compressed_image.sha256_hashes[1] == expected_resize_sha256
    )  # After resize to raw RGB
    # No hash for compression since it doesn't change visual content


@pytest.mark.asyncio
async def test_hash_pipeline_multiple_transformations() -> None:
    """Test hash accumulation through multiple resize operations."""
    # Create initial image
    original_bytes = create_test_png_image(400, 400)
    image = ImageData(original_bytes)
    original_hash = image.sha256_hashes[0]

    # First resize
    same_image = await resize_image(image)
    assert same_image is image  # Same object reference
    assert len(image.sha256_hashes) == AFTER_RESIZE_COUNT
    assert image.sha256_hashes[0] == original_hash
    first_resize_hash = image.sha256_hashes[1]

    # Second resize (from already resized raw RGB image)
    same_image_again = await resize_image(image)
    assert same_image_again is image  # Same object reference
    # Since it's already raw RGB of correct size, no additional hash
    # should be added
    assert len(image.sha256_hashes) == AFTER_RESIZE_COUNT
    assert image.sha256_hashes[0] == original_hash  # Original preserved
    assert image.sha256_hashes[1] == first_resize_hash  # First resize preserved


@pytest.mark.asyncio
async def test_hash_pipeline_compression_only() -> None:
    """Test that compression-only pipeline preserves original hashes."""
    # Create image and compress without any transformations
    original_bytes = create_test_png_image(200, 200)
    original_image = ImageData(original_bytes)
    original_sha256 = original_image.sha256_hashes[0]
    original_md5 = original_image.md5_hashes[0]

    # Store original data for comparison
    original_data = original_image.data

    # Compress directly
    compressed_image = compress_image(original_image)

    # Note: compressed_image is the same object as original_image (modified)
    assert compressed_image is original_image  # Same object reference

    # Should preserve exactly the same hash lists
    assert len(compressed_image.sha256_hashes) == ORIGINAL_HASH_COUNT
    assert len(compressed_image.md5_hashes) == ORIGINAL_HASH_COUNT
    assert compressed_image.sha256_hashes[0] == original_sha256
    assert compressed_image.md5_hashes[0] == original_md5

    # But data should be different (compressed)
    assert compressed_image.data != original_data


@pytest.mark.asyncio
async def test_hash_pipeline_format_conversion_only() -> None:
    """Test hash behavior with format conversion from PNG to raw RGB."""
    # Create PNG image at exact expected size
    original_bytes = create_test_png_image(EXPECTED_WIDTH, EXPECTED_HEIGHT)
    original_image = ImageData(original_bytes)
    original_sha256 = original_image.sha256_hashes[0]

    # Convert to raw RGB via resize function
    rgb_image = await resize_image(original_image)

    # Note: rgb_image is the same object as original_image (in-place)
    assert rgb_image is original_image  # Same object reference

    # Should have hashes for: original + conversion to raw RGB
    assert len(rgb_image.sha256_hashes) == AFTER_RESIZE_COUNT
    assert rgb_image.sha256_hashes[0] == original_sha256  # Original preserved

    # Final hash should match the raw RGB data
    final_hash = rgb_image.sha256_hashes[-1]
    expected_hash = hashlib.sha256(rgb_image.data).hexdigest()
    assert final_hash == expected_hash

    # Verify the data is now raw RGB format
    expected_size = EXPECTED_WIDTH * EXPECTED_HEIGHT * 3
    assert len(rgb_image.data) == expected_size


@pytest.mark.asyncio
async def test_empty_image_hash_behavior() -> None:
    """Test hash behavior with empty image data."""
    empty_image = ImageData(b"")

    # Should have hashes even for empty data
    assert len(empty_image.sha256_hashes) == 1
    assert len(empty_image.md5_hashes) == 1
    assert empty_image.sha256_hashes[0] == hashlib.sha256(b"").hexdigest()
    assert empty_image.md5_hashes[0] == hashlib.md5(b"").hexdigest()

    # Compression should preserve these hashes
    compressed = compress_image(empty_image)

    # Note: compressed is the same object as empty_image (modified in place)
    assert compressed is empty_image  # Same object reference

    # Hashes should be preserved (and since it's the same object, they will be)
    assert len(compressed.sha256_hashes) == ORIGINAL_HASH_COUNT
    assert len(compressed.md5_hashes) == ORIGINAL_HASH_COUNT
    assert compressed.sha256_hashes[0] == hashlib.sha256(b"").hexdigest()
    assert compressed.md5_hashes[0] == hashlib.md5(b"").hexdigest()
