"""Tests for hash list behavior throughout the transformation pipeline."""

import hashlib
from io import BytesIO

import pytest
from PIL import Image

from athena_client.client.consts import EXPECTED_HEIGHT, EXPECTED_WIDTH
from athena_client.client.models import ImageData
from athena_client.client.transformers.brotli_compressor import BrotliCompressor
from athena_client.client.transformers.image_resizer import ImageResizer
from athena_client.client.transformers.jpeg_converter import JpegConverter
from tests.utils.mock_async_iterator import MockAsyncIterator

# Constants for hash count assertions
ORIGINAL_HASH_COUNT = 1
AFTER_RESIZE_COUNT = 2
AFTER_JPEG_COUNT = 3


def create_test_png_image(width: int = 200, height: int = 200) -> bytes:
    """Create a test PNG image with specified dimensions."""
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


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
    resizer = ImageResizer(MockAsyncIterator([]))
    resized_image = await resizer.transform(original_image)

    # Verify resize added new hashes
    assert len(resized_image.sha256_hashes) == AFTER_RESIZE_COUNT
    assert len(resized_image.md5_hashes) == AFTER_RESIZE_COUNT
    assert (
        resized_image.sha256_hashes[0] == original_sha256
    )  # Original preserved
    assert resized_image.md5_hashes[0] == original_md5  # Original preserved

    # New hash should match the resized data
    expected_resize_sha256 = hashlib.sha256(resized_image.data).hexdigest()
    expected_resize_md5 = hashlib.md5(resized_image.data).hexdigest()
    assert resized_image.sha256_hashes[1] == expected_resize_sha256
    assert resized_image.md5_hashes[1] == expected_resize_md5

    # Step 2: Convert to JPEG (should add new hashes)
    jpeg_converter = JpegConverter(MockAsyncIterator([]))
    # Store JPEG data size before compression for comparison
    jpeg_image = await jpeg_converter.transform(resized_image)

    # Note: jpeg_image is the same object as resized_image (modified in place)
    assert jpeg_image is resized_image  # Same object reference

    # Verify JPEG conversion added new hashes
    assert len(jpeg_image.sha256_hashes) == AFTER_JPEG_COUNT
    assert len(jpeg_image.md5_hashes) == AFTER_JPEG_COUNT
    assert jpeg_image.sha256_hashes[0] == original_sha256  # Original preserved
    assert jpeg_image.md5_hashes[0] == original_md5  # Original preserved
    assert (
        jpeg_image.sha256_hashes[1] == expected_resize_sha256
    )  # Resize preserved
    assert jpeg_image.md5_hashes[1] == expected_resize_md5  # Resize preserved

    # New hash should match the JPEG data
    expected_jpeg_sha256 = hashlib.sha256(jpeg_image.data).hexdigest()
    expected_jpeg_md5 = hashlib.md5(jpeg_image.data).hexdigest()
    assert jpeg_image.sha256_hashes[2] == expected_jpeg_sha256
    assert jpeg_image.md5_hashes[2] == expected_jpeg_md5

    # Store data before compression for comparison
    jpeg_data_before_compression = jpeg_image.data
    jpeg_data_size_before = len(jpeg_image.data)

    # Step 3: Compress with Brotli (should preserve all hashes)
    compressor = BrotliCompressor(MockAsyncIterator([]))
    compressed_image = await compressor.transform(jpeg_image)

    # Note: compressed_image is the same object as jpeg_image (modified)
    assert compressed_image is jpeg_image  # Same object reference

    # Verify compression preserved all existing hashes
    assert (
        len(compressed_image.sha256_hashes) == AFTER_JPEG_COUNT
    )  # No new hashes added
    assert (
        len(compressed_image.md5_hashes) == AFTER_JPEG_COUNT
    )  # No new hashes added

    # Verify data was actually compressed
    assert compressed_image.data != jpeg_data_before_compression
    assert len(compressed_image.data) < jpeg_data_size_before

    # Final verification: Hash history tells the story
    assert compressed_image.sha256_hashes[0] == original_sha256  # Original PNG
    assert (
        compressed_image.sha256_hashes[1] == expected_resize_sha256
    )  # After resize
    assert (
        compressed_image.sha256_hashes[2] == expected_jpeg_sha256
    )  # After JPEG conversion
    # No hash for compression since it doesn't change visual content


@pytest.mark.asyncio
async def test_hash_pipeline_multiple_transformations() -> None:
    """Test hash accumulation through multiple resize operations."""
    # Create initial image
    original_bytes = create_test_png_image(400, 400)
    image = ImageData(original_bytes)
    original_hash = image.sha256_hashes[0]

    # Apply multiple resize operations
    resizer = ImageResizer(MockAsyncIterator([]))

    # First resize
    same_image = await resizer.transform(image)
    assert same_image is image  # Same object reference
    assert len(image.sha256_hashes) == AFTER_RESIZE_COUNT
    assert image.sha256_hashes[0] == original_hash
    first_resize_hash = image.sha256_hashes[1]

    # Second resize (from already resized image)
    same_image_again = await resizer.transform(image)
    assert same_image_again is image  # Same object reference
    assert len(image.sha256_hashes) == AFTER_JPEG_COUNT
    assert image.sha256_hashes[0] == original_hash  # Original preserved
    assert image.sha256_hashes[1] == first_resize_hash  # First resize preserved
    # Third hash should be the new resize
    assert image.sha256_hashes[2] == hashlib.sha256(image.data).hexdigest()


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
    compressor = BrotliCompressor(MockAsyncIterator([]))
    compressed_image = await compressor.transform(original_image)

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
    """Test hash behavior with format conversion but no resizing."""
    # Create PNG image at exact expected size (no resizing needed)

    original_bytes = create_test_png_image(EXPECTED_WIDTH, EXPECTED_HEIGHT)
    original_image = ImageData(original_bytes)
    original_sha256 = original_image.sha256_hashes[0]

    # Convert to JPEG (no resizing since it's already the right size)
    # First pass through resizer (should not change since size is correct)
    resizer = ImageResizer(MockAsyncIterator([]))
    maybe_resized = await resizer.transform(original_image)

    # Note: maybe_resized is the same object as original_image (in-place)
    assert maybe_resized is original_image  # Same object reference

    # Then convert to JPEG
    jpeg_converter = JpegConverter(MockAsyncIterator([]))
    jpeg_image = await jpeg_converter.transform(maybe_resized)

    # Note: jpeg_image is the same object as original_image (modified in place)
    assert jpeg_image is original_image  # Same object reference

    # Should have hashes for: original + resize + jpeg conversion
    assert len(jpeg_image.sha256_hashes) >= AFTER_RESIZE_COUNT
    assert jpeg_image.sha256_hashes[0] == original_sha256  # Original preserved

    # Final hash should match the JPEG data
    final_hash = jpeg_image.sha256_hashes[-1]
    expected_hash = hashlib.sha256(jpeg_image.data).hexdigest()
    assert final_hash == expected_hash


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
    compressor = BrotliCompressor(MockAsyncIterator([]))
    compressed = await compressor.transform(empty_image)

    # Note: compressed is the same object as empty_image (modified in place)
    assert compressed is empty_image  # Same object reference

    # Hashes should be preserved (and since it's the same object, they will be)
    assert len(compressed.sha256_hashes) == ORIGINAL_HASH_COUNT
    assert len(compressed.md5_hashes) == ORIGINAL_HASH_COUNT
    assert compressed.sha256_hashes[0] == hashlib.sha256(b"").hexdigest()
    assert compressed.md5_hashes[0] == hashlib.md5(b"").hexdigest()
