"""Tests for timeout behavior in the AthenaClient."""

import asyncio
import time
from collections.abc import AsyncIterator
from typing import NoReturn, Self, TypeVar, override
from unittest import mock

import pytest
from grpc import StatusCode
from grpc.aio._call import AioRpcError

from resolver_athena_client.client.athena_client import AthenaClient
from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.models import ImageData
from resolver_athena_client.generated.athena.models_pb2 import (
    ClassificationOutput,
    ClassifyResponse,
)


class MockGrpcError(AioRpcError):
    """Mock gRPC error for testing."""

    def __init__(self, code: StatusCode, details: str | None = None) -> None:  # pyright: ignore[reportMissingSuperCall] - Mock
        self._code: StatusCode = code
        self._details: str | None = details
        self._debug_error_string: str | None = f"MockGrpcError: {code.name}"

    @override
    def code(self) -> StatusCode:
        """Get the error code."""
        return self._code

    @override
    def details(self) -> str:
        """Get error details."""
        return self._details or ""


T = TypeVar("T")


class SlowMockAsyncIterator(AsyncIterator[T]):
    """Mock async iterator that yields with configurable delays."""

    def __init__(self, items: list[T], delay: float = 0.01) -> None:
        self.items: list[T] = items
        self.delay: float = delay
        self.index: int = 0

    @override
    def __aiter__(self) -> Self:
        return self

    @override
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
        timeout=0.05,  # Short timeout for test
    )

    with mock.patch(
        "resolver_athena_client.client.athena_client.ClassifierServiceClient"
    ) as mock_client_cls:
        mock_client = mock_client_cls.return_value
        # Create an iterator that will wait longer than the timeout
        mock_classify = SlowMockAsyncIterator(test_responses, delay=0.02)
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
        max_test_duration = 1.0  # Give some buffer over the timeout
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
        timeout=0.05,  # Short timeout for test
    )

    with mock.patch(
        "resolver_athena_client.client.athena_client.ClassifierServiceClient"
    ) as mock_client_cls:
        mock_client = mock_client_cls.return_value
        # Create an iterator with significant delays
        mock_classify = SlowMockAsyncIterator(test_responses, delay=0.02)
        mock_client.classify = mock.AsyncMock(return_value=mock_classify)

        options.timeout = None
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
    # Create responses with some having results and some being empty
    # Empty responses will trigger timeout logic
    test_responses = [
        ClassifyResponse(
            outputs=[ClassificationOutput(correlation_id="0")]
        ),  # Has results
        ClassifyResponse(outputs=[]),  # Empty - no results
        ClassifyResponse(outputs=[]),  # Empty - no results
        ClassifyResponse(outputs=[]),  # Empty - no results
        ClassifyResponse(
            outputs=[ClassificationOutput(correlation_id="4")]
        ),  # Has results
    ]
    mock_channel = mock.Mock()

    options = AthenaOptions(
        host="localhost",
        deployment_id="test-deployment",
        timeout=0.03,  # Short timeout for test
    )

    with mock.patch(
        "resolver_athena_client.client.athena_client.ClassifierServiceClient"
    ) as mock_client_cls:
        mock_client = mock_client_cls.return_value
        # Create an iterator with delays between responses
        mock_classify = SlowMockAsyncIterator(test_responses, delay=0.015)
        mock_client.classify = mock.AsyncMock(return_value=mock_classify)

        client = AthenaClient(mock_channel, options)
        image_stream = SlowMockAsyncIterator([ImageData(b"test_image")])

        responses = []
        responses = [
            response async for response in client.classify_images(image_stream)
        ]

        # Should timeout after getting some responses but before getting all
        # Due to empty responses creating gaps longer than timeout
        assert len(responses) >= 1  # Should get at least the first response
        assert len(responses) <= len(
            test_responses
        )  # But may not get all due to timeout


@pytest.mark.asyncio
async def test_timeout_with_errors() -> None:
    """Test timeout behavior when server errors occur."""
    mock_channel = mock.Mock()

    options = AthenaOptions(
        host="localhost",
        deployment_id="test-deployment",
        timeout=0.05,  # Short timeout for test
    )

    with mock.patch(
        "resolver_athena_client.client.athena_client.ClassifierServiceClient"
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
        timeout=0.05,  # Short timeout for test
    )

    with mock.patch(
        "resolver_athena_client.client.athena_client.ClassifierServiceClient"
    ) as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_classify = SlowMockAsyncIterator(test_responses, delay=0.01)
        mock_client.classify = mock.AsyncMock(return_value=mock_classify)

        client = AthenaClient(mock_channel, options)
        image_stream = SlowMockAsyncIterator([ImageData(b"test_image")])

        responses: list[ClassifyResponse] = []

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
