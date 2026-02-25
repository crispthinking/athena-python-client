"""Tests for WorkerBatcher with identity transforms (simple batching)."""

import asyncio

import pytest
from resolver_athena_client.generated.athena.models_pb2 import (
    ClassificationInput,
    ClassifyRequest,
    RequestEncoding,
)

from resolver_athena_client.client.transformers.worker_batcher import (
    WorkerBatcher,
)

# Test constants for various batch scenarios
FULL_BATCH_SIZE = 3
LARGE_BATCH_SIZE = 5
EXPECTED_ALL_ITEMS = 3

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
        self.data: list[ClassificationInput] = data
        self.delay: float = delay
        self.index: int = 0
        self.stopped: bool = False

    def __aiter__(self) -> "AsyncIteratorWithDelay":
        """Return self as async iterator."""
        return self

    async def __anext__(self) -> ClassificationInput:
        """Get next item or raise StopAsyncIteration.

        Raises:
            StopAsyncIteration: When all items are consumed or stopped

        """
        if self.index >= len(self.data) or self.stopped:
            raise StopAsyncIteration

        if self.delay > 0:
            await asyncio.sleep(self.delay)

        item = self.data[self.index]
        self.index += 1
        return item

    def stop(self) -> None:
        """Stop the iterator."""
        self.stopped = True


def create_test_input(data: bytes, correlation_id: str) -> ClassificationInput:
    """Create a test ClassificationInput."""
    return ClassificationInput(
        correlation_id=correlation_id,
        data=data,
        encoding=RequestEncoding.REQUEST_ENCODING_UNCOMPRESSED,
    )


# Identity transform for simple batching without transformation
async def identity_transform(item: ClassificationInput) -> ClassificationInput:
    """Identity transformation function."""
    return item


@pytest.fixture
def source_with_timeout() -> AsyncIteratorWithDelay:
    """Fixture to create a source with timeout for testing."""
    test_inputs = [
        create_test_input(b"test1", "id0"),
        create_test_input(b"test2", "id1"),
        create_test_input(b"test3", "id2"),
    ]
    return AsyncIteratorWithDelay(
        test_inputs, delay=0.002
    )  # Use 0.002s delay - larger than 0.001s timeout


@pytest.mark.asyncio
async def test_worker_batcher_basic() -> None:
    """Test basic batching functionality."""
    test_input = create_test_input(b"test1", "id0")
    source = AsyncIteratorWithDelay([test_input])
    batcher = WorkerBatcher(
        source=source,
        transformer_func=identity_transform,
        deployment_id="test-deployment",
        batch_timeout=0.001,
        keepalive_interval=0.001,  # Very short keepalive for immediate response
        num_workers=1,  # Single worker for simple case
    )

    # Should get one request with the item
    request = await anext(batcher)
    assert request is not None
    assert isinstance(request, ClassifyRequest)
    assert request.deployment_id == "test-deployment"
    assert len(request.inputs) == 1
    assert request.inputs[0].correlation_id == "id0"
    assert request.inputs[0].data == b"test1"

    # Cleanup
    await batcher.shutdown()


@pytest.mark.asyncio
async def test_worker_batcher_batching() -> None:
    """Test that multiple inputs are batched correctly."""
    test_inputs = [
        create_test_input(b"test1", "id0"),
        create_test_input(b"test2", "id1"),
        create_test_input(b"test3", "id2"),
    ]
    source = AsyncIteratorWithDelay(test_inputs)
    batcher = WorkerBatcher(
        source=source,
        transformer_func=identity_transform,
        deployment_id="test-deployment",
        max_batch_size=BATCH_SIZE_TWO,
        batch_timeout=0.001,
        keepalive_interval=0.1,
        num_workers=1,
    )

    # Should get first batch with 2 items
    request1 = await anext(batcher)
    assert request1 is not None
    assert isinstance(request1, ClassifyRequest)
    assert len(request1.inputs) == BATCH_SIZE_TWO
    assert request1.inputs[0].correlation_id == "id0"
    assert request1.inputs[1].correlation_id == "id1"

    # Should get second batch with remaining 1 item
    request2 = await anext(batcher)
    assert request2 is not None
    assert isinstance(request2, ClassifyRequest)
    assert len(request2.inputs) == 1
    assert request2.inputs[0].correlation_id == "id2"

    # Cleanup
    await batcher.shutdown()


@pytest.mark.asyncio
async def test_worker_batcher_timeout(
    source_with_timeout: AsyncIteratorWithDelay,
) -> None:
    """Test timeout behavior when items arrive slowly."""
    batcher = WorkerBatcher(
        source=source_with_timeout,
        transformer_func=identity_transform,
        deployment_id="test-deployment",
        max_batch_size=BATCH_SIZE_THREE,
        batch_timeout=0.001,  # Very short timeout to trigger timeout behavior
        keepalive_interval=0.1,
        num_workers=1,
    )

    # Should get partial batches due to timeout
    request1 = await anext(batcher)
    assert request1 is not None
    assert isinstance(request1, ClassifyRequest)
    # Due to timeout, should get less than max_batch_size
    assert len(request1.inputs) <= BATCH_SIZE_THREE
    assert len(request1.inputs) >= 1

    # Continue getting requests until we have all items
    all_received_items = list(request1.inputs)

    # Get more requests with a reasonable timeout
    try:
        for _ in range(5):  # Limit iterations to prevent infinite loop
            request = await asyncio.wait_for(anext(batcher), timeout=1.0)
            assert request is not None
            if request.inputs:  # Skip keepalives
                all_received_items.extend(request.inputs)
            if len(all_received_items) >= EXPECTED_ALL_ITEMS:
                break
    except asyncio.TimeoutError:
        pass  # Expected if no more items

    # Should have received all 3 items eventually
    assert len(all_received_items) >= EXPECTED_ALL_ITEMS

    # Cleanup
    await batcher.shutdown()


@pytest.mark.asyncio
async def test_worker_batcher_empty() -> None:
    """Test behavior with empty source."""
    source = AsyncIteratorWithDelay([])
    batcher = WorkerBatcher(
        source=source,
        transformer_func=identity_transform,
        deployment_id="test-deployment",
        batch_timeout=0.001,
        keepalive_interval=0.001,
        num_workers=1,
    )

    # Empty source should produce keepalive
    request = await anext(batcher)
    assert request is not None
    assert len(request.inputs) == 0  # Keepalive

    # Cleanup
    await batcher.shutdown()


@pytest.mark.asyncio
async def test_worker_batcher_exact_batch() -> None:
    """Test exact batch size handling."""
    test_inputs = [
        create_test_input(b"test1", f"id{i}") for i in range(BATCH_SIZE_THREE)
    ]
    source = AsyncIteratorWithDelay(test_inputs)
    batcher = WorkerBatcher(
        source=source,
        transformer_func=identity_transform,
        deployment_id="test-deployment",
        max_batch_size=BATCH_SIZE_THREE,
        batch_timeout=0.001,
        keepalive_interval=0.001,
        num_workers=1,
    )

    # Should get exactly one batch
    request = await anext(batcher)
    assert request is not None
    assert isinstance(request, ClassifyRequest)
    assert len(request.inputs) == BATCH_SIZE_THREE

    # Verify all items are present
    received_ids = {item.correlation_id for item in request.inputs}
    expected_ids = {f"id{i}" for i in range(BATCH_SIZE_THREE)}
    assert received_ids == expected_ids

    # Next should be keepalive since source is exhausted
    keepalive = await anext(batcher)
    assert keepalive is not None
    assert len(keepalive.inputs) == 0

    # Cleanup
    await batcher.shutdown()


@pytest.mark.asyncio
async def test_worker_batcher_edge_cases() -> None:
    """Test edge cases in batching."""
    # Create a source with many items to test partial batch handling
    test_inputs = [
        create_test_input(b"test1", f"id{i}")
        for i in range(LARGE_BATCH_SIZE + 1)
    ]
    source = AsyncIteratorWithDelay(test_inputs)

    # Create batcher with size that doesn't evenly divide input count
    batcher = WorkerBatcher(
        source=source,
        transformer_func=identity_transform,
        deployment_id="test-deployment",
        max_batch_size=BATCH_SIZE_TWO,
        batch_timeout=0.001,
        keepalive_interval=0.1,
        num_workers=1,
    )

    total_items_received = 0
    received_ids: set[str] = set()

    # Collect all batches
    for _ in range(10):  # Limit iterations
        try:
            request = await asyncio.wait_for(anext(batcher), timeout=0.5)
            assert request is not None
            if request.inputs:  # Skip keepalives
                total_items_received += len(request.inputs)
                for item in request.inputs:
                    received_ids.add(item.correlation_id)

                # Check batch size constraint
                assert len(request.inputs) <= BATCH_SIZE_TWO

            if total_items_received >= LARGE_BATCH_SIZE + 1:
                break
        except asyncio.TimeoutError:
            break

    # Should have received all items
    assert total_items_received == LARGE_BATCH_SIZE + 1
    expected_ids = {f"id{i}" for i in range(LARGE_BATCH_SIZE + 1)}
    assert received_ids == expected_ids

    # Cleanup
    await batcher.shutdown()


@pytest.mark.asyncio
async def test_worker_batcher_full_batch() -> None:
    """Test that when a batch becomes full, it is immediately returned."""
    test_inputs = [
        create_test_input(b"test1", f"id{i}")
        for i in range(FULL_BATCH_SIZE + 2)
    ]
    source = AsyncIteratorWithDelay(test_inputs)
    batcher = WorkerBatcher(
        source=source,
        transformer_func=identity_transform,
        deployment_id="test-deployment",
        max_batch_size=FULL_BATCH_SIZE,
        batch_timeout=0.001,
        keepalive_interval=0.1,
        num_workers=1,
    )

    # Should get first full batch
    request1 = await anext(batcher)
    assert request1 is not None
    assert len(request1.inputs) == FULL_BATCH_SIZE

    # Should get remaining items in next batch
    request2 = await anext(batcher)
    assert request2 is not None
    assert (
        len(request2.inputs) == REMAINING_BATCH_SIZE
    )  # FULL_BATCH_SIZE + 2 - FULL_BATCH_SIZE

    total_items = len(request1.inputs) + len(request2.inputs)
    assert total_items == FULL_BATCH_SIZE + 2

    # Cleanup
    await batcher.shutdown()


@pytest.mark.asyncio
async def test_worker_batcher_source_iteration_end() -> None:
    """Test that source ending during batch collection is handled properly."""
    test_inputs = [
        create_test_input(b"test1", "id0"),
        create_test_input(b"test2", "id1"),
    ]
    source = AsyncIteratorWithDelay(test_inputs)
    batcher = WorkerBatcher(
        source=source,
        transformer_func=identity_transform,
        deployment_id="test-deployment",
        max_batch_size=BATCH_SIZE_THREE,
        batch_timeout=0.001,
        keepalive_interval=0.001,
        num_workers=1,
    )

    # Should get a batch with available items (less than max_batch_size)
    request = await anext(batcher)
    assert request is not None
    assert len(request.inputs) == REMAINING_BATCH_SIZE  # All available items

    # Verify items are correct
    assert request.inputs[0].correlation_id == "id0"
    assert request.inputs[1].correlation_id == "id1"

    # Next should be keepalive since source is exhausted
    keepalive = await anext(batcher)
    assert keepalive is not None
    assert len(keepalive.inputs) == 0

    # Cleanup
    await batcher.shutdown()


@pytest.mark.asyncio
async def test_worker_batcher_iterator_end_no_timeout() -> None:
    """Test iterator ending without timeout."""
    test_inputs = [create_test_input(b"test1", "id0")]

    source = AsyncIteratorWithDelay(test_inputs, delay=0.005)

    # Use a fast timeout but longer than delay
    fast_timeout = 0.01
    batcher = WorkerBatcher(
        source=source,
        transformer_func=identity_transform,
        deployment_id="test-deployment",
        max_batch_size=BATCH_SIZE_TWO,
        batch_timeout=fast_timeout,
        keepalive_interval=0.1,
        num_workers=1,
    )

    # Should get the item before timeout
    request = await anext(batcher)
    assert request is not None
    assert len(request.inputs) == 1
    assert request.inputs[0].correlation_id == "id0"

    # Cleanup
    await batcher.shutdown()


@pytest.mark.asyncio
async def test_worker_batcher_transformation() -> None:
    """Test that transformation function is applied correctly."""
    test_input = create_test_input(b"original", "id0")
    source = AsyncIteratorWithDelay([test_input])

    # Transformation that modifies the data
    async def modify_transform(
        item: ClassificationInput,
    ) -> ClassificationInput:
        return ClassificationInput(
            correlation_id=item.correlation_id + "_modified",
            data=item.data + b"_transformed",
            encoding=item.encoding,
        )

    batcher = WorkerBatcher(
        source=source,
        transformer_func=modify_transform,
        deployment_id="test-deployment",
        batch_timeout=0.001,
        keepalive_interval=0.1,
        num_workers=1,
    )

    # Should get transformed item
    request = await anext(batcher)
    assert request is not None
    assert len(request.inputs) == 1
    assert request.inputs[0].correlation_id == "id0_modified"
    assert request.inputs[0].data == b"original_transformed"

    # Cleanup
    await batcher.shutdown()
