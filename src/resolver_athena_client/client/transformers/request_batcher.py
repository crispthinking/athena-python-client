"""Transform ClassificationInputs into batched ClassifyRequests."""

import asyncio
import logging
import time
from collections.abc import AsyncIterator

from resolver_athena_client.generated.athena.models_pb2 import (
    ClassificationInput,
    ClassifyRequest,
)


class RequestBatcher:
    """Batches ClassificationInputs into ClassifyRequests with keepalive."""

    def __init__(
        self,
        source: AsyncIterator[ClassificationInput],
        deployment_id: str,
        max_batch_size: int = 10,
        timeout: float = 0.1,
        keepalive_interval: float | None = None,
    ) -> None:
        """Initialize the batcher.

        Args:
        ----
            source: Iterator of ClassificationInputs to batch
            deployment_id: Deployment ID to use in requests
            max_batch_size: Maximum number of inputs per batch
            timeout: Max seconds to wait for additional items before batching
            keepalive_interval: Seconds between keepalive requests

        """
        self.source: AsyncIterator[ClassificationInput] = source
        self.deployment_id: str = deployment_id
        self.max_batch_size: int = max_batch_size
        self.timeout: float = timeout
        self.keepalive_interval: float = keepalive_interval or 30.0
        self._batch: list[ClassificationInput] = []
        self._last_send_time: float = time.time()
        self._stream_started: bool = False
        self._source_exhausted: bool = False
        self.logger: logging.Logger = logging.getLogger(__name__)

    @property
    def source_exhausted(self) -> bool:
        """Check if the input source is exhausted."""
        return self._source_exhausted

    def __aiter__(self) -> AsyncIterator[ClassifyRequest]:
        """Return self as an async iterator."""
        return self

    async def __anext__(self) -> ClassifyRequest:
        """Get the next batched request."""
        current_time = time.time()

        # Send keepalive if needed
        if self._should_send_keepalive(current_time):
            return self._create_keepalive_request(current_time)

        # Build batch
        await self._ensure_batch_has_items()

        # If source is exhausted and no batch items, wait for keepalive interval
        if self._source_exhausted and not self._batch:
            # Sleep until next keepalive time
            time_to_next_keepalive = self.keepalive_interval - (
                current_time - self._last_send_time
            )
            if time_to_next_keepalive > 0:
                await asyncio.sleep(time_to_next_keepalive)

            self.logger.info(
                "Source exhausted, sending keepalive to maintain stream"
            )
            return self._create_keepalive_request(time.time())

        await self._fill_batch()

        self._last_send_time = current_time
        return self._create_request()

    def _should_send_keepalive(self, current_time: float) -> bool:
        """Check if a keepalive request should be sent."""
        if self._batch:
            return False

        time_since_last_send = current_time - self._last_send_time
        return time_since_last_send >= self.keepalive_interval

    def _create_keepalive_request(self, current_time: float) -> ClassifyRequest:
        """Create a keepalive request to maintain persistent connection."""
        time_since_last = current_time - self._last_send_time
        self._last_send_time = current_time

        if not self._stream_started:
            self.logger.info(
                "Sending initial keepalive to establish persistent stream"
            )
            self._stream_started = True
        else:
            self.logger.info(
                "Sending keepalive after %.1fs to maintain connection",
                time_since_last,
            )

        return ClassifyRequest(deployment_id=self.deployment_id, inputs=[])

    async def _ensure_batch_has_items(self) -> None:
        """Ensure the batch has at least one item."""
        if not self._batch:
            try:
                item = await anext(self.source)
                self._batch.append(item)
            except StopAsyncIteration:
                self._source_exhausted = True
                if self._batch:
                    return
                # Don't raise StopAsyncIteration yet - let keepalives continue
                return

    async def _fill_batch(self) -> None:
        """Fill the batch up to max_batch_size."""
        while len(self._batch) < self.max_batch_size:
            try:
                item = await asyncio.wait_for(anext(self.source), self.timeout)
                self._batch.append(item)
            except StopAsyncIteration:  # noqa: PERF203 - Need to handle this whilst in the loop.
                # Iterator ended - no more items available
                self._source_exhausted = True
                break
            except asyncio.TimeoutError:
                # Timeout waiting for next item - send current batch
                break

    def _create_request(self) -> ClassifyRequest:
        """Create a ClassifyRequest from the current batch."""
        if not self._batch:
            msg = "No more inputs available"
            raise StopAsyncIteration(msg)

        batch = self._batch
        self._batch = []
        return ClassifyRequest(
            deployment_id=self.deployment_id,
            inputs=batch,
        )
