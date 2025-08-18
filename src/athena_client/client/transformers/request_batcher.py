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
    ) -> None:
        """Initialize the batcher.

        Args:
            source: Iterator of ClassificationInputs to batch
            deployment_id: Deployment ID to use in requests
            max_batch_size: Maximum number of inputs per batch

        """
        self.source = source
        self.deployment_id = deployment_id
        self.max_batch_size = max_batch_size
        self._batch: list[ClassificationInput] = []

    def __aiter__(self) -> AsyncIterator[ClassifyRequest]:
        """Return self as an async iterator."""
        return self

    async def __anext__(self) -> ClassifyRequest:
        """Get the next batched request."""
        if self._batch and len(self._batch) >= self.max_batch_size:
            return self._create_request()

        try:
            if not self._batch:
                first_item = await anext(self.source)
                self._batch.append(first_item)
        except StopAsyncIteration:
            if self._batch:
                return self._create_request()
            raise

        try:
            while len(self._batch) < self.max_batch_size:
                item = await asyncio.wait_for(anext(self.source), timeout=0.1)
                self._batch.append(item)
        except (StopAsyncIteration, asyncio.TimeoutError) as e:
            if self._batch:
                return self._create_request()
            raise StopAsyncIteration from e

        return self._create_request()

    def _create_request(self) -> ClassifyRequest:
        """Create a ClassifyRequest from the current batch."""
        batch = self._batch
        self._batch = []
        return ClassifyRequest(
            deployment_id=self.deployment_id,
            inputs=batch,
        )
