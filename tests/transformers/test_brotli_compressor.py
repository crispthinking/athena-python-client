from collections.abc import AsyncIterator

import brotli
import pytest

from athena_client.client.transformers.brotli_compressor import BrotliCompressor
from tests.utils.mock_async_iterator import MockAsyncIterator


@pytest.fixture
def source() -> AsyncIterator[bytes]:
    test_data = [b"test1", b"test2", b"test3"]
    return MockAsyncIterator(test_data)


@pytest.mark.asyncio
async def test_brotli_compressor_transform() -> None:
    compressor = BrotliCompressor(MockAsyncIterator([]))
    test_data = (
        b"Test data that is long enough to benefit from compression" * 10
    )

    # Test compression
    compressed = await compressor.transform(test_data)
    assert isinstance(compressed, bytes)
    assert len(compressed) < len(
        test_data
    )  # For this larger input, compression should reduce size

    # Verify data can be decompressed correctly
    decompressed = brotli.decompress(compressed)
    assert decompressed == test_data


@pytest.mark.asyncio
async def test_brotli_compressor_iteration(
    source: AsyncIterator[bytes],
) -> None:
    compressor = BrotliCompressor(source)

    # Test first item
    compressed = await anext(compressor)
    decompressed = brotli.decompress(compressed)
    assert decompressed == b"test1"

    # Test second item
    compressed = await anext(compressor)
    decompressed = brotli.decompress(compressed)
    assert decompressed == b"test2"

    # Test third item
    compressed = await anext(compressor)
    decompressed = brotli.decompress(compressed)
    assert decompressed == b"test3"

    # Test StopAsyncIteration
    with pytest.raises(StopAsyncIteration):
        await anext(compressor)


@pytest.mark.asyncio
async def test_brotli_compressor_empty_input() -> None:
    compressor = BrotliCompressor(MockAsyncIterator([]))
    compressed = await compressor.transform(b"")
    decompressed = brotli.decompress(compressed)
    assert decompressed == b""
