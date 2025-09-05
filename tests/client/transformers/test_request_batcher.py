"""Tests for RequestBatcher transformer."""

import asyncio
import time
from collections.abc import AsyncIterator

import pytest

from athena_client.client.transformers.request_batcher import RequestBatcher
from athena_client.generated.athena.athena_pb2 import (
    ClassificationInput,
    ClassifyRequest,
    RequestEncoding,
)

# Test constants for various batch scenarios
FULL_BATCH_SIZE = 3
LARGE_BATCH_SIZE = 5

# Constants for test configuration
BATCH_SIZE_TWO = 2
BATCH_SIZE_THREE = 3
REMAINING_BATCH_SIZE = 2  # Size of remaining items in partial batch
DELAY_LONGER_THAN_TIMEOUT = 0.01  # > timeout used in tests


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
    return AsyncIteratorWithDelay(
        test_inputs, delay=0.002
    )  # Use 0.002s delay - larger than 0.001s timeout


@pytest.mark.asyncio
async def test_request_batcher_basic() -> None:
    test_input = create_test_input(b"test1", "id0")
    source = AsyncIteratorWithDelay([test_input])
    batcher = RequestBatcher(
        source,
        deployment_id="test-deployment",
        timeout=0.001,
        keepalive_interval=0.001,  # Very short keepalive for immediate response
    )

    # Should get one request with the item
    request = await anext(batcher)
    assert isinstance(request, ClassifyRequest)
    assert request.deployment_id == "test-deployment"
    assert len(request.inputs) == 1
    assert request.inputs[0].correlation_id == "id0"
    assert request.inputs[0].data == b"test1"

    # Verify source is exhausted by checking the batcher's internal state
    assert batcher.source_exhausted


@pytest.mark.asyncio
async def test_request_batcher_batching() -> None:
    test_inputs = [
        create_test_input(b"test1", "id0"),
        create_test_input(b"test2", "id1"),
        create_test_input(b"test3", "id2"),
    ]
    source = AsyncIteratorWithDelay(test_inputs)
    batcher = RequestBatcher(
        source,
        deployment_id="test-deployment",
        max_batch_size=BATCH_SIZE_TWO,
        timeout=0.001,
        keepalive_interval=0.001,
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

    # Verify source is exhausted
    assert batcher.source_exhausted


@pytest.mark.asyncio
async def test_request_batcher_timeout(
    source_with_timeout: AsyncIteratorWithDelay,
) -> None:
    batcher = RequestBatcher(
        source_with_timeout,
        deployment_id="test-deployment",
        max_batch_size=BATCH_SIZE_THREE,
        timeout=0.001,  # Very short timeout to trigger timeout behavior
        keepalive_interval=0.1,
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

    # Verify source is exhausted
    assert batcher.source_exhausted


@pytest.mark.asyncio
async def test_request_batcher_empty() -> None:
    source = AsyncIteratorWithDelay([])
    batcher = RequestBatcher(
        source,
        deployment_id="test-deployment",
        timeout=0.001,
        keepalive_interval=0.001,
    )

    # Empty source should produce keepalive
    request = await anext(batcher)
    assert len(request.inputs) == 0  # Keepalive


@pytest.mark.asyncio
async def test_request_batcher_exact_batch() -> None:
    test_inputs = [
        create_test_input(b"test1", f"id{i}") for i in range(BATCH_SIZE_THREE)
    ]
    source = AsyncIteratorWithDelay(test_inputs)
    batcher = RequestBatcher(
        source,
        deployment_id="test-deployment",
        max_batch_size=BATCH_SIZE_THREE,
        timeout=0.001,
        keepalive_interval=0.001,
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

    # After consuming all items, source should be exhausted
    # Need to trigger one more iteration to confirm exhaustion
    try:
        await anext(batcher)  # This should be a keepalive
        assert batcher.source_exhausted
    except StopAsyncIteration:
        assert batcher.source_exhausted


@pytest.mark.asyncio
async def test_request_batcher_edge_cases() -> None:
    """Test edge cases in request batching."""
    # Create a source with many items to test partial batch handling
    test_inputs = [
        create_test_input(b"test1", f"id{i}")
        for i in range(LARGE_BATCH_SIZE + 1)
    ]
    source = AsyncIteratorWithDelay(test_inputs)

    # Create batcher with size that doesn't evenly divide input count
    batcher = RequestBatcher(
        source,
        deployment_id="test-deployment",
        max_batch_size=BATCH_SIZE_TWO,
        timeout=0.001,
        keepalive_interval=0.001,
    )

    # First batch: should be full
    request = await anext(batcher)
    assert len(request.inputs) == BATCH_SIZE_TWO
    assert [inp.correlation_id for inp in request.inputs] == ["id0", "id1"]

    # Second batch: should be full
    request = await anext(batcher)
    assert len(request.inputs) == BATCH_SIZE_TWO
    assert [inp.correlation_id for inp in request.inputs] == ["id2", "id3"]

    # Third batch: should be full
    request = await anext(batcher)
    assert len(request.inputs) == BATCH_SIZE_TWO
    assert [inp.correlation_id for inp in request.inputs] == ["id4", "id5"]

    # After consuming all items, source should be exhausted
    # Need to trigger one more iteration to confirm exhaustion
    try:
        await anext(batcher)  # This should be a keepalive
        assert batcher.source_exhausted
    except StopAsyncIteration:
        assert batcher.source_exhausted


@pytest.mark.asyncio
async def test_request_batcher_full_batch() -> None:
    """Test that when a batch becomes full, it is immediately returned."""
    test_inputs = [
        create_test_input(b"test1", f"id{i}")
        for i in range(FULL_BATCH_SIZE + 2)
    ]
    source = AsyncIteratorWithDelay(test_inputs)
    batcher = RequestBatcher(
        source,
        deployment_id="test-deployment",
        max_batch_size=FULL_BATCH_SIZE,
        timeout=0.001,
        keepalive_interval=0.001,
    )

    # First batch should be returned immediately when it hits max size
    request = await anext(batcher)
    assert len(request.inputs) == FULL_BATCH_SIZE
    assert [inp.correlation_id for inp in request.inputs] == [
        "id0",
        "id1",
        "id2",
    ]

    # Second batch should contain the remaining items
    request = await anext(batcher)
    assert len(request.inputs) == REMAINING_BATCH_SIZE
    assert [inp.correlation_id for inp in request.inputs] == ["id3", "id4"]

    # Verify source is exhausted
    assert batcher.source_exhausted


@pytest.mark.asyncio
async def test_request_batcher_stop_iteration_during_batch() -> None:
    test_inputs = [
        create_test_input(b"test1", "id0"),
        create_test_input(b"test2", "id1"),
    ]
    source = AsyncIteratorWithDelay(test_inputs)
    batcher = RequestBatcher(
        source,
        deployment_id="test-deployment",
        max_batch_size=BATCH_SIZE_THREE,
        timeout=0.001,
        keepalive_interval=0.001,
    )

    # First batch should have both items even though
    # it's less than max_batch_size
    request = await anext(batcher)
    assert len(request.inputs) == BATCH_SIZE_TWO
    assert request.inputs[0].correlation_id == "id0"
    assert request.inputs[1].correlation_id == "id1"

    # Verify source is exhausted
    assert batcher.source_exhausted


@pytest.mark.asyncio
async def test_request_batcher_iterator_end_no_timeout() -> None:
    """Test that batches are returned immediately when iterator ends."""

    # Create a source with 2 items - no delays
    test_inputs = [
        create_test_input(b"test1", "id0"),
        create_test_input(b"test2", "id1"),
    ]
    source = AsyncIteratorWithDelay(test_inputs, delay=0)  # No delay

    # Use a fast timeout but longer than delay
    fast_timeout = 0.01
    batcher = RequestBatcher(
        source,
        deployment_id="test-deployment",
        max_batch_size=3,  # Larger than available items
        timeout=fast_timeout,
        keepalive_interval=0.1,
    )

    # Measure time for first batch
    start_time = time.time()
    request = await anext(batcher)
    elapsed = time.time() - start_time

    # Should get both items immediately when iterator ends
    # without waiting for timeout
    expected_items = 2
    assert len(request.inputs) == expected_items
    assert request.inputs[0].correlation_id == "id0"
    assert request.inputs[1].correlation_id == "id1"

    # Should complete much faster than timeout
    # Allow some buffer for test execution overhead
    assert elapsed < fast_timeout * 2, (
        f"Took {elapsed}s, should be much less than {fast_timeout}s"
    )

    # Next request should be a keepalive since source is exhausted
    request = await anext(batcher)
    assert len(request.inputs) == 0  # Keepalive has no inputs
