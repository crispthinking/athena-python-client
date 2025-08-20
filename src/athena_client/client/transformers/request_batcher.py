"""Transform ClassificationInputs into batched ClassifyRequests."""

import asyncio
from collections.abc import AsyncIterator

from athena_client.generated.athena.athena_pb2 import (
    ClassificationInput,
    ClassifyRequest,
)


class RequestBatcher:
    """Batches ClassificationInputs into ClassifyRequests."""

    def __init__(
        self,
        source: AsyncIterator[ClassificationInput],
        deployment_id: str,
        max_batch_size: int = 10,
        timeout: float = 0.1,
    ) -> None:
        """Initialize the batcher.

        Args:
            source: Iterator of ClassificationInputs to batch
            deployment_id: Deployment ID to use in requests
            max_batch_size: Maximum number of inputs per batch
            timeout: Max seconds to wait for additional items before batching

        """
        self.source = source
        self.deployment_id = deployment_id
        self.max_batch_size = max_batch_size
        self.timeout = timeout
        self._batch: list[ClassificationInput] = []

    def __aiter__(self) -> AsyncIterator[ClassifyRequest]:
        """Return self as an async iterator."""
        return self

    async def __anext__(self) -> ClassifyRequest:
        """Get the next batched request."""
        try:
            # Always get at least one item
            if not self._batch:
                self._batch.append(await anext(self.source))

            # Try to get more items up to max_batch_size
            try:
                while len(self._batch) < self.max_batch_size:
                    item = await asyncio.wait_for(
                        anext(self.source), self.timeout
                    )
                    self._batch.append(item)
            except (asyncio.TimeoutError, StopAsyncIteration):
                pass

            return self._create_request()

        except StopAsyncIteration:
            if self._batch:
                return self._create_request()
            raise

    def _create_request(self) -> ClassifyRequest:
        """Create a ClassifyRequest from the current batch."""
        batch = self._batch
        self._batch = []
        return ClassifyRequest(
            deployment_id=self.deployment_id,
            inputs=batch,
        )
