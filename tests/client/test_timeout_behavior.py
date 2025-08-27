"""Tests for timeout behavior in the AthenaClient."""

import asyncio
import time
from collections.abc import AsyncIterator
from typing import NoReturn, Self, TypeVar
from unittest import mock

import pytest
from grpc import StatusCode
from grpc.aio._call import AioRpcError

from athena_client.client.athena_client import AthenaClient
from athena_client.client.athena_options import AthenaOptions
from athena_client.client.models import ImageData
from athena_client.generated.athena.athena_pb2 import (
    ClassificationOutput,
    ClassifyResponse,
)


class MockGrpcError(AioRpcError):
    """Mock gRPC error for testing."""

    def __init__(self, code: StatusCode, details: str | None = None) -> None:
        self._code = code
        self._details: str | None = details
        self._debug_error_string: str | None = f"MockGrpcError: {code.name}"

    def code(self) -> StatusCode:
        """Get the error code."""
        return self._code

    def details(self) -> str:
        """Get error details."""
        return self._details or ""

    def debug_error_string(self) -> str:
        """Get debug error string."""
        return self._debug_error_string or ""


T = TypeVar("T")


class SlowMockAsyncIterator(AsyncIterator[T]):
    """Mock async iterator that yields with configurable delays."""

    def __init__(self, items: list[T], delay: float = 0.1) -> None:
        self.items = items
        self.delay = delay
        self.index = 0

    def __aiter__(self) -> Self:
        return self

    async def __anext__(self) -> T:
        if self.index >= len(self.items):
            raise StopAsyncIteration
        await asyncio.sleep(self.delay)
        item = self.items[self.index]
        self.index += 1
        return item


@pytest.mark.asyncio
async def test_timeout_behavior() -> None:
    """Test that default timeout behavior stops after 120s without responses."""
    test_responses = [
        ClassifyResponse(outputs=[ClassificationOutput(correlation_id="1")])
    ]
    mock_channel = mock.Mock()

    options = AthenaOptions(
        host="localhost",
        deployment_id="test-deployment",
        timeout=0.5,  # Short timeout for test
    )

    with mock.patch(
        "athena_client.client.athena_client.ClassifierServiceClient"
    ) as mock_client_cls:
        mock_client = mock_client_cls.return_value
        # Create an iterator that will wait longer than the timeout
        mock_classify = SlowMockAsyncIterator(test_responses, delay=0.2)
        mock_client.classify = mock.AsyncMock(return_value=mock_classify)

        client = AthenaClient(mock_channel, options)
        image_stream = SlowMockAsyncIterator([ImageData(b"test_image")])

        responses = []
        start_time = time.time()

        # Should timeout and stop after 120s
        responses = [
            response async for response in client.classify_images(image_stream)
        ]

        duration = time.time() - start_time
        max_test_duration = 121  # Give some buffer over the 120s timeout
        assert (
            duration < max_test_duration
        )  # Ensure we don't wait longer than timeout
        assert len(responses) == 1  # Should get first response before timeout


@pytest.mark.asyncio
async def test_infinite_timeout() -> None:
    """Test that setting timeout=None allows infinite streaming."""
    test_responses = [
        ClassifyResponse(outputs=[ClassificationOutput(correlation_id=str(i))])
        for i in range(5)
    ]
    mock_channel = mock.Mock()

    options = AthenaOptions(
        host="localhost",
        deployment_id="test-deployment",
        timeout=0.5,  # Short timeout for test
    )

    with mock.patch(
        "athena_client.client.athena_client.ClassifierServiceClient"
    ) as mock_client_cls:
        mock_client = mock_client_cls.return_value
        # Create an iterator with significant delays
        mock_classify = SlowMockAsyncIterator(test_responses, delay=0.2)
        mock_client.classify = mock.AsyncMock(return_value=mock_classify)

        options.timeout = None  # type: ignore[assignment]
        client = AthenaClient(mock_channel, options)
        image_stream = SlowMockAsyncIterator([ImageData(b"test_image")])

        responses = []
        responses = [
            response async for response in client.classify_images(image_stream)
        ]

        # Should get all responses despite delays
        assert len(responses) == len(test_responses)
        for i, response in enumerate(responses):
            assert response.outputs[0].correlation_id == str(i)


@pytest.mark.asyncio
async def test_custom_timeout() -> None:
    """Test that a custom timeout value is respected."""
    test_responses = [
        ClassifyResponse(outputs=[ClassificationOutput(correlation_id=str(i))])
        for i in range(5)
    ]
    mock_channel = mock.Mock()

    options = AthenaOptions(
        host="localhost",
        deployment_id="test-deployment",
        timeout=0.5,  # Short timeout for test
    )

    with mock.patch(
        "athena_client.client.athena_client.ClassifierServiceClient"
    ) as mock_client_cls:
        mock_client = mock_client_cls.return_value
        # Create an iterator with delays just under and over our custom timeout
        mock_classify = SlowMockAsyncIterator(test_responses, delay=0.3)
        mock_client.classify = mock.AsyncMock(return_value=mock_classify)

        options.timeout = 0.2  # Set short custom timeout
        client = AthenaClient(mock_channel, options)
        image_stream = SlowMockAsyncIterator([ImageData(b"test_image")])

        responses = []
        responses = [
            response async for response in client.classify_images(image_stream)
        ]

        # Should get fewer responses due to timeout
        assert len(responses) < len(test_responses)


@pytest.mark.asyncio
async def test_timeout_with_errors() -> None:
    """Test timeout behavior when server errors occur."""
    mock_channel = mock.Mock()

    options = AthenaOptions(
        host="localhost",
        deployment_id="test-deployment",
        timeout=0.5,  # Short timeout for test
    )

    with mock.patch(
        "athena_client.client.athena_client.ClassifierServiceClient"
    ) as mock_client_cls:
        mock_client = mock_client_cls.return_value
        # Use our custom MockGrpcError
        error = MockGrpcError(
            code=StatusCode.INTERNAL,
            details="Test error",
        )
        mock_client.classify = mock.AsyncMock(side_effect=error)

        client = AthenaClient(mock_channel, options)
        image_stream = SlowMockAsyncIterator([ImageData(b"test_image")])

        # With persistent streams, errors end the stream naturally
        responses = [
            response async for response in client.classify_images(image_stream)
        ]

        # Should get no responses due to error
        assert len(responses) == 0


@pytest.mark.asyncio
async def test_timeout_with_cancellation() -> None:
    """Test timeout behavior with asyncio cancellation."""
    test_responses = [
        ClassifyResponse(outputs=[ClassificationOutput(correlation_id=str(i))])
        for i in range(10)
    ]
    mock_channel = mock.Mock()

    options = AthenaOptions(
        host="localhost",
        deployment_id="test-deployment",
        timeout=0.5,  # Short timeout for test
    )

    with mock.patch(
        "athena_client.client.athena_client.ClassifierServiceClient"
    ) as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_classify = SlowMockAsyncIterator(test_responses, delay=0.1)
        mock_client.classify = mock.AsyncMock(return_value=mock_classify)

        client = AthenaClient(mock_channel, options)
        image_stream = SlowMockAsyncIterator([ImageData(b"test_image")])

        responses = []

        async def _cancel_stream() -> NoReturn:
            """Helper function to cancel the stream."""
            raise asyncio.CancelledError

        target_responses = 2
        try:
            async for response in client.classify_images(image_stream):
                responses.append(response)
                if len(responses) == target_responses:
                    # Cancel after target number of responses
                    await _cancel_stream()
        except asyncio.CancelledError:
            pass
        finally:
            assert len(responses) == target_responses


# NOTE: Timeout behavior has been improved to only apply while input is active.
# Once the input iterator ends, the stream waits indefinitely for remaining
# responses. The timeout is now based on time between responses rather than
# total stream time. This addresses the issue where streams would timeout even
# when input had finished and responses were still pending (e.g., sent 26400,
# received 3437, timed out at 120s).
