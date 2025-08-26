"""Mock gRPC stream call for testing."""

from collections.abc import AsyncIterator, Callable
from typing import Generic, TypeVar

import grpc
from grpc.aio import Call, Metadata, StreamStreamCall

RequestT = TypeVar("RequestT")
ResponseT = TypeVar("ResponseT")


class MockStreamCall(Generic[RequestT, ResponseT]):
    """Mock for gRPC stream stream calls.

    This class provides a simplified mock implementation of StreamStreamCall
    that can be used for testing streaming gRPC methods. The mock maintains
    a list of pre-configured responses and supports required gRPC call
    patterns.

    Args:
        responses: List of response objects to return when streaming.
    """

    def __init__(self, responses: list[ResponseT]) -> None:
        """Initialize with response list."""
        self.responses = responses.copy()
        self.call_count = 0

    def __call__(
        self,
        request_iter: AsyncIterator[RequestT],
        *,
        timeout: float | None = None,
        wait_for_ready: bool = True,
    ) -> StreamStreamCall[RequestT, ResponseT]:
        """Handle calls with request iterator.

        Args:
            request_iter: Iterator of request messages.

        Returns:
            StreamStreamCall for response streaming.
        """
        self.call_count += 1
        # Store parameters for potential test verification
        self._last_timeout = timeout
        self._last_wait_for_ready = wait_for_ready
        return StreamCallMock(request_iter, self.responses)


class StreamCallMock(StreamStreamCall[RequestT, ResponseT]):
    """Mock implementation of StreamStreamCall."""

    def __init__(
        self, request_iter: AsyncIterator[RequestT], responses: list[ResponseT]
    ) -> None:
        """Initialize with request iterator and responses."""
        super().__init__()
        self._request_iter = request_iter
        self._responses = responses.copy()
        self._done = False
        self._cancelled = False
        self._done_callbacks: list[Callable[[Call], None]] = []

    def __aiter__(self) -> AsyncIterator[ResponseT]:
        """Get async iterator over responses."""
        return self

    async def __anext__(self) -> ResponseT:
        """Get next response message.

        Returns:
            Next response from pre-configured list.

        Raises:
            StopAsyncIteration: When no more responses.
        """
        if not self._responses:
            raise StopAsyncIteration
        return self._responses.pop(0)

    async def read(self) -> ResponseT:
        """Read next response message.

        Returns:
            Next response from pre-configured list.
        """
        return await self.__anext__()

    async def write(self, request: RequestT) -> None:
        """Write a request message (no-op).

        Args:
            request: Request message to write.
        """

    async def done_writing(self) -> None:
        """Signal end of request stream."""
        self._done = True

    def add_done_callback(self, callback: Callable[[Call], None]) -> None:
        """Register completion callback.

        Args:
            callback: Function to call on completion.
        """
        self._done_callbacks.append(callback)
        if self._done:
            callback(self)

    def time_remaining(self) -> float | None:
        """Get remaining timeout time.

        Returns:
            None since timeouts are not implemented.
        """
        return None

    def cancel(self) -> bool:
        """Cancel the call.

        Returns:
            True if this was the first cancellation.
        """
        if not self._cancelled:
            self._cancelled = True
            self._done = True
            for callback in self._done_callbacks:
                callback(self)
            return True
        return False

    def cancelled(self) -> bool:
        """Check if call was cancelled.

        Returns:
            True if cancel() was called.
        """
        return self._cancelled

    async def code(self) -> grpc.StatusCode:
        """Get status code.

        Returns:
            Always OK in this mock.
        """
        return grpc.StatusCode.OK

    async def details(self) -> str:
        """Get error details.

        Returns:
            Empty string since errors not implemented.
        """
        return ""

    async def initial_metadata(self) -> Metadata:
        """Get initial metadata.

        Returns:
            Empty metadata tuple since metadata not implemented.
        """
        return Metadata()

    async def trailing_metadata(self) -> Metadata:
        """Get trailing metadata.

        Returns:
            Empty metadata tuple since metadata not implemented.
        """
        return Metadata()

    def done(self) -> bool:
        """Check if call is complete.

        Returns:
            True if done_writing() was called.
        """
        return self._done

    async def wait_for_connection(self) -> None:
        """Wait for connection (no-op)."""
