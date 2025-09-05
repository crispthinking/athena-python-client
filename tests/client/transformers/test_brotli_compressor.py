from collections.abc import AsyncIterator

import brotli
import pytest

from athena_client.client.models import ImageData
from athena_client.client.transformers.brotli_compressor import BrotliCompressor
from tests.utils.mock_async_iterator import MockAsyncIterator


@pytest.fixture
def source() -> AsyncIterator[ImageData]:
    test_data = [ImageData(b"test1"), ImageData(b"test2"), ImageData(b"test3")]
    return MockAsyncIterator(test_data)


@pytest.mark.asyncio
async def test_brotli_compressor_transform() -> None:
    compressor = BrotliCompressor(MockAsyncIterator([]))
    test_bytes = (
        b"Test data that is long enough to benefit from compression" * 10
    )
    test_data = ImageData(test_bytes)

    # Test compression
    compressed = await compressor.transform(test_data)
    assert isinstance(compressed, ImageData)
    assert len(compressed.data) < len(
        test_bytes
    )  # For this larger input, compression should reduce size

    # Verify data can be decompressed correctly
    decompressed = brotli.decompress(compressed.data)
    assert decompressed == test_bytes


@pytest.mark.asyncio
async def test_brotli_compressor_iteration(
    source: AsyncIterator[ImageData],
) -> None:
    compressor = BrotliCompressor(source)

    # Test first item
    compressed = await anext(compressor)
    decompressed = brotli.decompress(compressed.data)
    assert decompressed == b"test1"

    # Test second item
    compressed = await anext(compressor)
    decompressed = brotli.decompress(compressed.data)
    assert decompressed == b"test2"

    # Test third item
    compressed = await anext(compressor)
    decompressed = brotli.decompress(compressed.data)
    assert decompressed == b"test3"

    # Test StopAsyncIteration
    with pytest.raises(StopAsyncIteration):
        await anext(compressor)


@pytest.mark.asyncio
async def test_brotli_compressor_empty_input() -> None:
    compressor = BrotliCompressor(MockAsyncIterator([]))
    test_data = ImageData(b"")
    compressed = await compressor.transform(test_data)
    decompressed = brotli.decompress(compressed.data)
    assert decompressed == b""


@pytest.mark.asyncio
async def test_brotli_compressor_preserves_hashes() -> None:
    """Test that BrotliCompressor preserves original hashes.

    Compression operations should preserve existing hash lists since they don't
    modify the visual content of the image.
    """
    compressor = BrotliCompressor(MockAsyncIterator([]))
    test_bytes = b"Test data for hash preservation verification"
    test_data = ImageData(test_bytes)

    # Store original hashes and data for comparison
    original_sha256 = test_data.sha256_hashes.copy()
    original_md5 = test_data.md5_hashes.copy()
    original_data = test_data.data

    # Compress the data
    compressed = await compressor.transform(test_data)

    # Note: compressed is the same object as test_data (modified in place)
    assert compressed is test_data  # Same object reference

    # Verify the data is actually compressed (different bytes)
    assert compressed.data != original_data
    assert len(compressed.data) != len(original_data)

    # Verify hashes are preserved (not recalculated)
    assert compressed.sha256_hashes == original_sha256
    assert compressed.md5_hashes == original_md5

    # Verify decompressed data matches original
    decompressed = brotli.decompress(compressed.data)
    assert decompressed == test_bytes
