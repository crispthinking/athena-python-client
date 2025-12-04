"""Asyncio worker-based batching system for improved throughput."""

import asyncio
import contextlib
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Generic, TypeVar

from resolver_athena_client.generated.athena.models_pb2 import (
    ClassificationInput,
    ClassifyRequest,
)

T = TypeVar("T")


class WorkerBatcher(Generic[T]):
    """Asyncio worker-based batcher with concurrent processing and buffering."""

    def __init__(  # noqa: PLR0913
        self,
        source: AsyncIterator[T],
        transformer_func: Callable[[T], Awaitable[ClassificationInput]],
        deployment_id: str,
        max_batch_size: int = 10,
        num_workers: int = 4,
        queue_size: int = 100,
        keepalive_interval: float = 30.0,
        batch_timeout: float = 0.1,
    ) -> None:
        """Initialize the worker batcher.

        Args:
        ----
            source: Source iterator of items to process
            transformer_func: Function to transform items (e.g., image
                processing)
            deployment_id: Deployment ID for requests
            max_batch_size: Maximum items per batch
            num_workers: Number of concurrent worker tasks
            queue_size: Size of internal processing queue
            keepalive_interval: Seconds between keepalive requests
            batch_timeout: Max seconds to wait before sending partial batch


        """
        self.source: AsyncIterator[T] = source
        self.transformer_func: Callable[[T], Awaitable[ClassificationInput]] = (
            transformer_func
        )
        self.deployment_id: str = deployment_id
        self.max_batch_size: int = max_batch_size
        self.num_workers: int = num_workers
        self.keepalive_interval: float = keepalive_interval
        self.batch_timeout: float = batch_timeout

        # Internal queues and state - use Optional[T] to handle None sentinel
        self.input_queue: asyncio.Queue[T | None] = asyncio.Queue(
            maxsize=queue_size
        )
        self.output_queue: asyncio.Queue[ClassificationInput] = asyncio.Queue(
            maxsize=queue_size
        )
        self.processed_items: list[ClassificationInput] = []

        # Coordination
        self.workers_started: bool = False
        self.source_exhausted: bool = False
        self.workers_done: bool = False
        self.last_send_time: float = time.time()

        # Tasks
        self.worker_tasks: list[asyncio.Task[None]] = []
        self.feeder_task: asyncio.Task[None] | None = None
        self.batcher_task: asyncio.Task[None] | None = None

        self.logger: logging.Logger = logging.getLogger(__name__)

    async def __aiter__(self) -> AsyncIterator[ClassifyRequest | None]:
        """Start workers and return batched requests."""
        if not self.workers_started:
            await self._start_workers()

        # Main batching loop - never terminate automatically
        while True:
            try:
                request = await self._get_next_batch()
                yield request
            except asyncio.CancelledError:  # noqa: PERF203 needed for proper handling of cancellation
                self.logger.debug(
                    "Batch generation cancelled, attempting keepalive"
                )
                try:
                    keepalive_request = self._create_keepalive_request(
                        time.time()
                    )
                    yield keepalive_request
                    # Continue the loop to keep the stream alive
                    continue
                except (ValueError, RuntimeError) as e:
                    self.logger.warning(
                        "Failed to send keepalive after cancellation: %s", e
                    )
                    # Continue trying to keep stream alive even after errors
                    await asyncio.sleep(1.0)  # Brief delay before retry
                    continue

    async def _start_workers(self) -> None:
        """Start all worker tasks."""
        self.logger.debug("Starting %d worker tasks", self.num_workers)

        # Start feeder task (reads from source)
        self.feeder_task = asyncio.create_task(self._feed_input_queue())

        # Start worker tasks (process items)
        for i in range(self.num_workers):
            task = asyncio.create_task(self._worker(f"worker-{i}"))
            self.worker_tasks.append(task)

        # Start batcher task (collects processed items)
        self.batcher_task = asyncio.create_task(self._collect_processed_items())

        self.workers_started = True

    async def _feed_input_queue(self) -> None:
        """Feed items from source into input queue."""
        try:
            async for item in self.source:
                await self.input_queue.put(item)

            # Signal end of input
            self.source_exhausted = True

            # Send sentinel values to stop workers
            for _ in range(self.num_workers):
                await self.input_queue.put(None)

            self.logger.debug("Source exhausted, sent stop signals to workers")

        except asyncio.CancelledError:
            self.logger.debug(
                "Feeder task cancelled, marking source as exhausted"
            )
            self.source_exhausted = True
            # Send stop signals to workers
            for _ in range(self.num_workers):
                with contextlib.suppress(asyncio.CancelledError):
                    await self.input_queue.put(None)
        except Exception:
            self.logger.exception("Error in feeder task")
            raise

    async def _worker(self, worker_id: str) -> None:
        """Worker task that processes items."""
        self.logger.debug("%s started", worker_id)

        try:
            while True:
                try:
                    # Get item from input queue
                    item = await self.input_queue.get()
                except asyncio.CancelledError:
                    self.logger.debug(
                        "%s cancelled while waiting for input", worker_id
                    )
                    break

                # Check for stop signal
                if item is None:
                    self.logger.debug("%s received stop signal", worker_id)
                    break

                try:
                    # Process the item
                    processed_item = await self._process_item(item)

                    # Put processed item in output queue
                    await self.output_queue.put(processed_item)

                except asyncio.CancelledError:
                    self.logger.debug(
                        "%s cancelled while processing item", worker_id
                    )
                    break
                except Exception:
                    self.logger.exception("%s error processing item", worker_id)
                    # Continue processing other items

        except Exception:
            self.logger.exception("%s crashed", worker_id)
            raise
        finally:
            self.logger.debug("%s finished", worker_id)

    async def _process_item(self, item: T) -> ClassificationInput:
        """Process a single item through the transformation pipeline."""
        # Apply transformation function (handles resize, compression, etc.)
        return await self.transformer_func(item)

    async def _collect_processed_items(self) -> None:
        """Collect processed items from workers."""
        active_workers = self.num_workers

        while active_workers > 0 or not self.output_queue.empty():
            try:
                # Wait for processed item with timeout
                processed_item = await asyncio.wait_for(
                    self.output_queue.get(), timeout=1.0
                )

                # Add to batch
                self.processed_items.append(processed_item)

            except asyncio.TimeoutError:  # noqa: PERF203 Needed for timeout handling
                # No items available, continue waiting
                if self.source_exhausted and self.output_queue.empty():
                    break
            except asyncio.CancelledError:
                # If cancelled, always continue collecting to keep workers
                # pulling
                self.logger.debug(
                    "Item collection cancelled, workers continue pulling "
                    "from queue"
                )
                # Never break - always continue to keep the stream alive
                continue

        self.workers_done = True
        self.logger.debug("All workers finished processing")

    async def _get_next_batch(self) -> ClassifyRequest | None:
        """Get the next batch of requests."""
        current_time = time.time()

        # Check if we should send a keepalive
        if self._should_send_keepalive(current_time):
            return self._create_keepalive_request(current_time)

        # Wait for batch to fill up or timeout
        while (
            len(self.processed_items) < self.max_batch_size
            and not self.workers_done
        ):
            try:
                await asyncio.wait_for(
                    self._wait_for_items(), timeout=self.batch_timeout
                )
            except asyncio.TimeoutError:  # noqa: PERF203 needed for proper handling of cancellation
                # Timeout - send current batch if we have items
                if self.processed_items:
                    break
                # No items yet, check keepalive
                if self._should_send_keepalive(time.time()):
                    return self._create_keepalive_request(time.time())
                continue
            except asyncio.CancelledError:
                # If cancelled, always continue to keep workers pulling
                self.logger.debug(
                    "Batch wait cancelled, workers continue pulling"
                )
                # Always continue the loop to keep workers active
                continue

        # Create batch request if we have items
        if self.processed_items:
            return self._create_batch_request(current_time)

        # Keep stream alive with keepalives to continue receiving shared queue
        # results
        if self.workers_done:
            self.logger.debug(
                "All work complete, sending keepalive to continue "
                "receiving shared queue results"
            )
            return self._create_keepalive_request(time.time())

        # Send keepalive to maintain connection while work is ongoing
        if self._should_send_keepalive(current_time):
            return self._create_keepalive_request(current_time)

        # If no conditions match, wait briefly and send appropriate request
        # This ensures we never return None which would terminate the stream
        await asyncio.sleep(0.1)
        return self._create_keepalive_request(time.time())

    async def _wait_for_items(self) -> None:
        """Wait for items to become available."""
        while (
            len(self.processed_items) < self.max_batch_size
            and not self.workers_done
        ):
            try:
                await asyncio.sleep(0.01)  # Small delay to prevent busy waiting
            except asyncio.CancelledError:
                # If sleep is cancelled, log it but keep waiting for items
                self.logger.debug(
                    "Sleep cancelled in _wait_for_items, "
                    "workers continue pulling"
                )
                # Don't re-raise the cancellation - keep workers active
            if self.processed_items:
                break

    def _should_send_keepalive(self, current_time: float) -> bool:
        """Check if we should send a keepalive request."""
        if self.processed_items:
            return False  # Have real data to send

        time_since_last = current_time - self.last_send_time
        return time_since_last >= self.keepalive_interval

    def _create_keepalive_request(self, current_time: float) -> ClassifyRequest:
        """Create a keepalive request."""
        self.last_send_time = current_time
        self.logger.debug("Sending keepalive request")

        return ClassifyRequest(deployment_id=self.deployment_id, inputs=[])

    def _create_batch_request(self, current_time: float) -> ClassifyRequest:
        """Create a batch request from processed items."""
        batch_items = self.processed_items[: self.max_batch_size]
        self.processed_items = self.processed_items[self.max_batch_size :]

        self.last_send_time = current_time

        self.logger.debug(
            "Creating batch request with %d items", len(batch_items)
        )

        return ClassifyRequest(
            deployment_id=self.deployment_id, inputs=batch_items
        )

    async def _cleanup(self) -> None:
        """Clean up worker tasks."""
        self.logger.debug("Cleaning up worker tasks")

        # Cancel and wait for tasks with timeout to avoid hanging
        cleanup_timeout = 5.0  # 5 seconds timeout for cleanup

        if self.feeder_task and not self.feeder_task.done():
            _ = self.feeder_task.cancel()
            try:
                await asyncio.wait_for(
                    self.feeder_task, timeout=cleanup_timeout
                )
            except (asyncio.CancelledError, asyncio.TimeoutError):
                self.logger.debug("Feeder task cleanup completed/timed out")

        if self.batcher_task and not self.batcher_task.done():
            _ = self.batcher_task.cancel()
            try:
                await asyncio.wait_for(
                    self.batcher_task, timeout=cleanup_timeout
                )
            except (asyncio.CancelledError, asyncio.TimeoutError):
                self.logger.debug("Batcher task cleanup completed/timed out")

        # Clean up worker tasks
        for i, task in enumerate(self.worker_tasks):
            if not task.done():
                _ = task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=cleanup_timeout)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    self.logger.debug(
                        "Worker task %d cleanup completed/timed out", i
                    )

        self.logger.debug("Worker cleanup complete")

    async def shutdown(self) -> None:
        """Explicitly shutdown the worker batcher and clean up resources.

        This should only be called when manually terminating the stream,
        not during normal operation completion.
        """
        self.logger.debug("Explicit shutdown requested, cleaning up resources")
        await self._cleanup()
