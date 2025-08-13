"""Tests for RequestBatcher transformer."""

import asyncio
from collections.abc import AsyncIterator

import pytest

from athena_client.client.transformers.request_batcher import RequestBatcher
from athena_client.generated.athena.athena_pb2 import (
    ClassificationInput,
    ClassifyRequest,
    RequestEncoding,
)

# Constants for test configuration
BATCH_SIZE_TWO = 2
BATCH_SIZE_THREE = 3
DELAY_LONGER_THAN_TIMEOUT = 0.2  # > default timeout of 0.1


class AsyncIteratorWithDelay:
    def __init__(
        self, data: list[ClassificationInput], delay: float = 0
    ) -> None:
        """Initialize with data and delay.

        Args:
            data: List of ClassificationInput objects to yield
            delay: Delay in seconds between items, defaults to 0

        """
        self.data = data
        self.delay = delay
        self.index = 0
        self.stopped = False

    def __aiter__(self) -> "AsyncIteratorWithDelay":
        """Return self as async iterator."""
        return self

    async def __anext__(self) -> ClassificationInput:
        """Get next item or raise StopAsyncIteration.

        If delay is set, will wait for delay seconds before yielding item.
        """
        if self.index >= len(self.data) or self.stopped:
            raise StopAsyncIteration
        if self.delay:
            await asyncio.sleep(self.delay)
        item = self.data[self.index]
        self.index += 1
        return item


def create_test_input(
    data: bytes = b"test", correlation_id: str | None = None
) -> ClassificationInput:
    return ClassificationInput(
        affiliate="test-affiliate",
        correlation_id=correlation_id or "test-correlation",
        data=data,
        encoding=RequestEncoding.REQUEST_ENCODING_BROTLI,
    )


@pytest.fixture
def source() -> AsyncIterator[ClassificationInput]:
    test_inputs = [
        create_test_input(b"test1", "id0"),
        create_test_input(b"test2", "id1"),
        create_test_input(b"test3", "id2"),
        create_test_input(b"test4", "id3"),
        create_test_input(b"test5", "id4"),
    ]
    return AsyncIteratorWithDelay(test_inputs)


@pytest.fixture
def source_with_timeout() -> AsyncIterator[ClassificationInput]:
    # First item is immediate, subsequent items have delay > timeout
    test_inputs = [
        create_test_input(b"test1", "id0"),
        create_test_input(b"test2", "id1"),
        create_test_input(b"test3", "id2"),
    ]
    return AsyncIteratorWithDelay(test_inputs, delay=DELAY_LONGER_THAN_TIMEOUT)


@pytest.mark.asyncio
async def test_request_batcher_basic() -> None:
    test_input = create_test_input(b"test1", "id0")
    source = AsyncIteratorWithDelay([test_input])
    batcher = RequestBatcher(source, deployment_id="test-deployment")

    # Should get one request with the item
    request = await anext(batcher)
    assert isinstance(request, ClassifyRequest)
    assert request.deployment_id == "test-deployment"
    assert len(request.inputs) == 1
    assert request.inputs[0].correlation_id == "id0"
    assert request.inputs[0].data == b"test1"

    # Should raise StopAsyncIteration after that
    with pytest.raises(StopAsyncIteration):
        await anext(batcher)


@pytest.mark.asyncio
async def test_request_batcher_batching() -> None:
    test_inputs = [
        create_test_input(b"test1", "id0"),
        create_test_input(b"test2", "id1"),
        create_test_input(b"test3", "id2"),
    ]
    source = AsyncIteratorWithDelay(test_inputs)
    batcher = RequestBatcher(
        source, deployment_id="test-deployment", max_batch_size=BATCH_SIZE_TWO
    )

    # First batch should have max_batch_size items
    request = await anext(batcher)
    assert len(request.inputs) == BATCH_SIZE_TWO
    assert request.inputs[0].correlation_id == "id0"
    assert request.inputs[1].correlation_id == "id1"

    # Second batch should have remaining item
    request = await anext(batcher)
    assert len(request.inputs) == 1
    assert request.inputs[0].correlation_id == "id2"

    # Should raise StopAsyncIteration after that
    with pytest.raises(StopAsyncIteration):
        await anext(batcher)


@pytest.mark.asyncio
async def test_request_batcher_timeout(
    source_with_timeout: AsyncIteratorWithDelay,
) -> None:
    batcher = RequestBatcher(
        source_with_timeout,
        deployment_id="test-deployment",
        max_batch_size=BATCH_SIZE_THREE,
    )

    # First batch should have one item due to timeout waiting for more
    request = await anext(batcher)
    assert len(request.inputs) == 1
    assert request.inputs[0].correlation_id == "id0"

    # Second request should also have one item due to timeout
    request = await anext(batcher)
    assert len(request.inputs) == 1
    assert request.inputs[0].correlation_id == "id1"

    # Third request should have the last item
    request = await anext(batcher)
    assert len(request.inputs) == 1
    assert request.inputs[0].correlation_id == "id2"

    # Should raise StopAsyncIteration after that
    with pytest.raises(StopAsyncIteration):
        await anext(batcher)


@pytest.mark.asyncio
async def test_request_batcher_empty() -> None:
    source = AsyncIteratorWithDelay([])
    batcher = RequestBatcher(source, deployment_id="test-deployment")

    with pytest.raises(StopAsyncIteration):
        await anext(batcher)


@pytest.mark.asyncio
async def test_request_batcher_exact_batch() -> None:
    test_inputs = [
        create_test_input(b"test1", f"id{i}") for i in range(BATCH_SIZE_THREE)
    ]
    source = AsyncIteratorWithDelay(test_inputs)
    batcher = RequestBatcher(
        source, deployment_id="test-deployment", max_batch_size=BATCH_SIZE_THREE
    )

    # Should get one request with all items
    request = await anext(batcher)
    assert len(request.inputs) == BATCH_SIZE_THREE
    assert [
        request_input.correlation_id for request_input in request.inputs
    ] == [
        "id0",
        "id1",
        "id2",
    ]

    # Should raise StopAsyncIteration after that
    with pytest.raises(StopAsyncIteration):
        await anext(batcher)


@pytest.mark.asyncio
async def test_request_batcher_stop_iteration_during_batch() -> None:
    test_inputs = [
        create_test_input(b"test1", "id0"),
        create_test_input(b"test2", "id1"),
    ]
    source = AsyncIteratorWithDelay(test_inputs)
    batcher = RequestBatcher(
        source, deployment_id="test-deployment", max_batch_size=BATCH_SIZE_THREE
    )

    # First batch should have both items even though
    # it's less than max_batch_size
    request = await anext(batcher)
    assert len(request.inputs) == BATCH_SIZE_TWO
    assert request.inputs[0].correlation_id == "id0"
    assert request.inputs[1].correlation_id == "id1"

    # Should raise StopAsyncIteration after that
    with pytest.raises(StopAsyncIteration):
        await anext(batcher)
