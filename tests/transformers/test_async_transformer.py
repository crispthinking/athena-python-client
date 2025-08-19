"""Tests for AsyncTransformer base class."""

from collections.abc import AsyncIterator
from typing import TypeVar

import pytest

from athena_client.client.transformers.async_transformer import AsyncTransformer
from tests.utils.mock_async_iterator import MockAsyncIterator

T = TypeVar("T")


class DummyTransformer(AsyncTransformer[bytes, bytes]):
    """Test implementation of AsyncTransformer."""

    async def transform(self, data: bytes) -> bytes:
        """Simply return the input data."""
        return data


class MockTransformer(AsyncTransformer[bytes, T]):
    """Mock implementation for testing abstract base class."""

    async def transform(self, data: bytes) -> T:
        """Mock transform method that raises NotImplementedError."""
        message = "Subclasses must implement this method"
        raise NotImplementedError(message)


@pytest.fixture
def source() -> AsyncIterator[bytes]:
    """Fixture providing an async iterator of test data."""
    test_data = [b"test1", b"test2", b"test3"]
    return MockAsyncIterator(test_data)


@pytest.mark.asyncio
async def test_transformer_iteration(source: AsyncIterator[bytes]) -> None:
    transformer = DummyTransformer(source)

    # Test first item
    item = await anext(transformer)
    assert item == b"test1"

    # Test second item
    item = await anext(transformer)
    assert item == b"test2"

    # Test third item
    item = await anext(transformer)
    assert item == b"test3"

    # Test StopAsyncIteration
    with pytest.raises(StopAsyncIteration):
        await anext(transformer)


@pytest.mark.asyncio
async def test_abstract_transform_raises() -> None:
    """Test that the abstract transform method raises NotImplementedError."""
    mock_source = MockAsyncIterator([b"test"])
    transformer = MockTransformer[bytes](mock_source)

    with pytest.raises(
        NotImplementedError, match="Subclasses must implement this method"
    ):
        await transformer.transform(b"test")
