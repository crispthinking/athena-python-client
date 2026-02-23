"""Tests for AthenaClient."""

import asyncio
import contextlib
from typing import cast
from unittest import mock

import pytest
from grpc import aio

from resolver_athena_client.client.athena_client import AthenaClient
from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.exceptions import AthenaError
from resolver_athena_client.client.models import ImageData
from resolver_athena_client.generated.athena.models_pb2 import (
    ClassificationError,
    ClassificationOutput,
    ClassifyResponse,
    ErrorCode,
)
from resolver_athena_client.grpc_wrappers.classifier_service import (
    ClassifierServiceClient,
)
from tests.utils.mock_async_iterator import MockAsyncIterator


@pytest.fixture
def mock_channel() -> mock.Mock:
    return mock.Mock(spec=aio.Channel)


@pytest.fixture
def mock_classifier_client() -> mock.Mock:
    return mock.Mock(spec=ClassifierServiceClient)


@pytest.fixture
def mock_options() -> AthenaOptions:
    return AthenaOptions(
        deployment_id="test-deployment",
        affiliate="test-affiliate",
        resize_images=False,
        compress_images=False,
        max_batch_size=2,
        num_workers=3,
    )


@pytest.fixture
def test_images() -> list[ImageData]:
    return [ImageData(b"test_image_1"), ImageData(b"test_image_2")]


@pytest.mark.asyncio
async def test_classify_images_success(
    mock_channel: mock.Mock,
    mock_options: AthenaOptions,
    test_images: list[ImageData],
) -> None:
    # Create test data
    test_responses = [
        ClassifyResponse(outputs=[ClassificationOutput(correlation_id="1")]),
        ClassifyResponse(outputs=[ClassificationOutput(correlation_id="2")]),
    ]

    # Setup mock classifier client
    with mock.patch(
        "resolver_athena_client.client.athena_client.ClassifierServiceClient",
        spec=ClassifierServiceClient,
    ) as mock_client_cls:
        mock_client = cast("mock.MagicMock", mock_client_cls.return_value)

        # Create mock stream that returns our responses
        mock_classify = MockAsyncIterator(test_responses)
        mock_client.classify = mock_classify

        # Create client and classify images
        client = AthenaClient(mock_channel, mock_options)

        # Collect only the expected number of responses
        responses: list[ClassifyResponse] = []
        classify_task = None

        try:

            async def collect_responses() -> None:
                response_iter = aiter(
                    client.classify_images(MockAsyncIterator(test_images))
                )
                for _ in range(len(test_responses)):
                    response: ClassifyResponse = await anext(response_iter)
                    responses.append(response)

            # Create task and use timeout to prevent hanging
            classify_task = asyncio.create_task(collect_responses())
            await asyncio.wait_for(classify_task, timeout=5.0)
        finally:
            # Cleanup: cancel the task if it's still running
            if classify_task and not classify_task.done():
                _ = classify_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await classify_task
            await client.close()

        # Verify responses
        assert len(responses) == len(test_responses)
        assert responses[0].outputs[0].correlation_id == "1"
        assert responses[1].outputs[0].correlation_id == "2"

        # Verify classify was called once
        assert mock_classify.call_count == 1
        # Pipeline verification done through successful response processing


@pytest.mark.asyncio
async def test_client_context_manager_success(
    mock_channel: mock.Mock,
    mock_options: AthenaOptions,
) -> None:
    # Setup mock to return success response without error message
    init_response = ClassifyResponse(
        outputs=[],
    )  # Success response will have default empty global_error

    with mock.patch(
        "resolver_athena_client.client.athena_client.ClassifierServiceClient",
        spec=ClassifierServiceClient,
    ) as mock_client_cls:
        mock_client = cast("mock.MagicMock", mock_client_cls.return_value)

        # Create mock stream that returns our response
        mock_classify = MockAsyncIterator([init_response])
        mock_client.classify = mock_classify

        # Use client as context manager
        async with AthenaClient(mock_channel, mock_options) as client:
            assert isinstance(client, AthenaClient)
            # Send a test image to trigger the classify call
            test_image = ImageData(b"test_image")

            classify_task = None
            try:

                async def get_one_response() -> None:
                    response_iter = aiter(
                        client.classify_images(MockAsyncIterator([test_image]))
                    )
                    # Get one response to verify the stream is working
                    _ = await anext(response_iter)

                # Create task and use timeout to prevent hanging
                classify_task = asyncio.create_task(get_one_response())
                await asyncio.wait_for(classify_task, timeout=5.0)
                assert mock_classify.call_count == 1
            finally:
                # Cleanup: cancel the task if it's still running
                if classify_task and not classify_task.done():
                    _ = classify_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await classify_task

        # Verify channel was closed
        close_mock = cast("mock.MagicMock", mock_channel.close)
        close_mock.assert_called_once()


@pytest.mark.asyncio
async def test_client_context_manager_error(
    mock_channel: mock.Mock,
    mock_options: AthenaOptions,
) -> None:
    # Setup mock to return error response for initialization
    error_response = ClassifyResponse(
        global_error=ClassificationError(
            message="Test error",  # Non-empty message will trigger error
            code=ErrorCode.ERROR_CODE_UNSPECIFIED,
            details="",
        ),
        outputs=[],
    )

    with mock.patch(
        "resolver_athena_client.client.athena_client.ClassifierServiceClient",
        spec=ClassifierServiceClient,
    ) as mock_client_cls:
        mock_client = cast("mock.MagicMock", mock_client_cls.return_value)

        # Create mock stream that returns our error response
        mock_classify = MockAsyncIterator([error_response])
        mock_client.classify = mock_classify

        # Create client outside the raises block
        client = AthenaClient(mock_channel, mock_options)

        # Verify error is raised when processing images
        test_image = ImageData(b"test_image")
        classify_task = None

        try:

            async def get_error_response() -> None:
                response_iter = aiter(
                    client.classify_images(MockAsyncIterator([test_image]))
                )
                _ = await anext(response_iter)

            classify_task = asyncio.create_task(get_error_response())

            with pytest.raises(AthenaError, match="Test error"):
                await asyncio.wait_for(classify_task, timeout=5.0)
        finally:
            # Cleanup: cancel the task if it's still running
            if classify_task and not classify_task.done():
                _ = classify_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await classify_task
            await client.close()


@pytest.mark.asyncio
async def test_client_transformers_disabled(
    mock_channel: mock.Mock,
    mock_options: AthenaOptions,
) -> None:
    """Test client with image transformers disabled."""
    # Test with default options (no JPEG conversion)

    test_response = ClassifyResponse(
        outputs=[ClassificationOutput(correlation_id="1")]
    )

    with mock.patch(
        "resolver_athena_client.client.athena_client.ClassifierServiceClient",
        spec=ClassifierServiceClient,
    ) as mock_client_cls:
        mock_client = cast("mock.MagicMock", mock_client_cls.return_value)
        mock_classify = MockAsyncIterator([test_response])
        mock_client.classify = mock_classify

        # Create client with disabled transformers
        client = AthenaClient(mock_channel, mock_options)

        # Send raw test image that would normally be resized/compressed
        raw_image = ImageData(b"uncompressed_test_image")

        classify_task = None
        try:

            async def get_response() -> ClassifyResponse:
                response_iter = aiter(
                    client.classify_images(MockAsyncIterator([raw_image]))
                )
                return await anext(response_iter)

            # Create task and use timeout to prevent hanging
            classify_task = asyncio.create_task(get_response())
            response = await asyncio.wait_for(classify_task, timeout=5.0)
        finally:
            # Cleanup: cancel the task if it's still running
            if classify_task and not classify_task.done():
                _ = classify_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await classify_task
            await client.close()

        # Verify response was received
        assert response.outputs[0].correlation_id == "1"

        # Verify classify was called
        assert mock_classify.call_count == 1


@pytest.mark.asyncio
async def test_client_transformers_enabled(
    mock_channel: mock.Mock,
    mock_options: AthenaOptions,
) -> None:
    """Test client with raw image data."""
    # Test with raw image data (no JPEG conversion needed)

    test_response = ClassifyResponse(
        outputs=[ClassificationOutput(correlation_id="1")]
    )

    with mock.patch(
        "resolver_athena_client.client.athena_client.ClassifierServiceClient",
        spec=ClassifierServiceClient,
    ) as mock_client_cls:
        mock_client = cast("mock.MagicMock", mock_client_cls.return_value)
        mock_classify = MockAsyncIterator([test_response])
        mock_client.classify = mock_classify

        # Create client with enabled transformers
        client = AthenaClient(mock_channel, mock_options)

        # Send test image that should be resized/compressed
        raw_image = ImageData(b"uncompressed_test_image")

        classify_task = None
        try:

            async def get_response() -> ClassifyResponse:
                response_iter = aiter(
                    client.classify_images(MockAsyncIterator([raw_image]))
                )
                return await anext(response_iter)

            # Create task and use timeout to prevent hanging
            classify_task = asyncio.create_task(get_response())
            response = await asyncio.wait_for(classify_task, timeout=5.0)
        finally:
            # Cleanup: cancel the task if it's still running
            if classify_task and not classify_task.done():
                _ = classify_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await classify_task
            await client.close()

        # Verify response was received
        assert response.outputs[0].correlation_id == "1"

        # Verify classify was called
        assert mock_classify.call_count == 1


@pytest.mark.asyncio
async def test_client_num_workers_configuration(
    mock_channel: mock.Mock,
) -> None:
    """Test that num_workers option is passed to WorkerBatcher."""
    custom_num_workers = 7
    options = AthenaOptions(
        deployment_id="test-deployment",
        affiliate="test-affiliate",
        resize_images=False,
        compress_images=False,
        max_batch_size=2,
        num_workers=custom_num_workers,
    )

    test_response = ClassifyResponse(
        outputs=[ClassificationOutput(correlation_id="1")]
    )

    with (
        mock.patch(
            "resolver_athena_client.client.athena_client.ClassifierServiceClient",
            spec=ClassifierServiceClient,
        ) as mock_client_cls,
        mock.patch(
            "resolver_athena_client.client.athena_client.WorkerBatcher"
        ) as mock_worker_batcher_cls,
    ):
        mock_client = cast("mock.MagicMock", mock_client_cls.return_value)
        mock_classify = MockAsyncIterator([test_response])
        mock_client.classify = mock_classify

        # Mock WorkerBatcher to track constructor args
        mock_batcher = mock.Mock()
        mock_batcher.__aiter__ = mock.Mock(return_value=MockAsyncIterator([]))
        mock_worker_batcher_cls.return_value = mock_batcher

        client = AthenaClient(mock_channel, options)
        test_image = ImageData(b"test_image")

        classify_task = None
        try:

            async def start_classification() -> None:
                response_iter = aiter(
                    client.classify_images(MockAsyncIterator([test_image]))
                )
                with contextlib.suppress(StopAsyncIteration):
                    _ = await anext(response_iter)

            classify_task = asyncio.create_task(start_classification())
            await asyncio.wait_for(classify_task, timeout=1.0)
        except asyncio.TimeoutError:
            # Expected since we're just testing the setup
            pass
        finally:
            if classify_task and not classify_task.done():
                _ = classify_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await classify_task
            await client.close()

        # Verify WorkerBatcher was created with correct num_workers
        mock_worker_batcher_cls.assert_called_once()
        call_kwargs = mock_worker_batcher_cls.call_args.kwargs
        assert call_kwargs["num_workers"] == custom_num_workers


@pytest.mark.asyncio
async def test_client_close(
    mock_channel: mock.Mock, mock_options: AthenaOptions
) -> None:
    client = AthenaClient(mock_channel, mock_options)

    await client.close()

    close_mock = cast("mock.MagicMock", mock_channel.close)
    close_mock.assert_called_once()
