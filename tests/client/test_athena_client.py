"""Tests for AthenaClient."""

from unittest import mock

import pytest
from grpc import aio

from athena_client.client.athena_client import AthenaClient
from athena_client.client.athena_options import AthenaOptions
from athena_client.client.exceptions import AthenaError
from athena_client.generated.athena.athena_pb2 import (
    ClassificationError,
    ClassificationOutput,
    ClassifyResponse,
    ErrorCode,
)
from athena_client.grpc_wrappers.classifier_service import (
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
    )


@pytest.fixture
def test_images() -> list[bytes]:
    return [b"test_image_1", b"test_image_2"]


@pytest.mark.asyncio
async def test_classify_images_success(
    mock_channel: mock.Mock,
    mock_options: AthenaOptions,
    test_images: list[bytes],
) -> None:
    # Create test data
    test_responses = [
        ClassifyResponse(outputs=[ClassificationOutput(correlation_id="1")]),
        ClassifyResponse(outputs=[ClassificationOutput(correlation_id="2")]),
    ]

    # Setup mock classifier client
    with mock.patch(
        "athena_client.client.athena_client.ClassifierServiceClient"
    ) as mock_client_cls:
        mock_client = mock_client_cls.return_value

        # Create mock stream that returns our responses
        mock_classify = MockAsyncIterator(test_responses)
        mock_client.classify = mock_classify

        # Create client and classify images
        client = AthenaClient(mock_channel, mock_options)
        responses = [
            response
            async for response in client.classify_images(
                MockAsyncIterator(test_images)
            )
        ]

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
        "athena_client.client.athena_client.ClassifierServiceClient"
    ) as mock_client_cls:
        mock_client = mock_client_cls.return_value

        # Create mock stream that returns our response
        mock_classify = MockAsyncIterator([init_response])
        mock_client.classify = mock_classify

        # Use client as context manager
        async with AthenaClient(mock_channel, mock_options) as client:
            assert isinstance(client, AthenaClient)
            # Send a test image to trigger the classify call
            test_image = b"test_image"
            async for _ in client.classify_images(
                MockAsyncIterator([test_image])
            ):
                pass
            assert mock_classify.call_count == 1

        # Verify channel was closed
        mock_channel.close.assert_called_once()


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
        "athena_client.client.athena_client.ClassifierServiceClient"
    ) as mock_client_cls:
        mock_client = mock_client_cls.return_value

        # Create mock stream that returns our error response
        mock_classify = MockAsyncIterator([error_response])
        mock_client.classify = mock_classify

        # Create client outside the raises block
        client = AthenaClient(mock_channel, mock_options)

        # Verify error is raised when processing images
        test_image = b"test_image"
        with pytest.raises(AthenaError, match="Test error"):
            async for _ in client.classify_images(
                MockAsyncIterator([test_image])
            ):
                pass


@pytest.mark.asyncio
async def test_client_transformers_disabled(
    mock_channel: mock.Mock,
    mock_options: AthenaOptions,
) -> None:
    """Test client with image transformers disabled."""
    # Explicitly override options to ensure transformers are disabled
    mock_options.resize_images = False
    mock_options.compress_images = False

    test_response = ClassifyResponse(
        outputs=[ClassificationOutput(correlation_id="1")]
    )

    with (
        mock.patch(
            "athena_client.client.athena_client.ClassifierServiceClient"
        ) as mock_client_cls,
        mock.patch(
            "athena_client.client.athena_client.ImageResizer"
        ) as mock_resizer,
        mock.patch(
            "athena_client.client.athena_client.BrotliCompressor"
        ) as mock_compressor,
    ):
        mock_client = mock_client_cls.return_value
        mock_classify = MockAsyncIterator([test_response])
        mock_client.classify = mock_classify

        # Create client with disabled transformers
        client = AthenaClient(mock_channel, mock_options)

        # Send raw test image that would normally be resized/compressed
        raw_image = b"uncompressed_test_image"
        responses = [
            response
            async for response in client.classify_images(
                MockAsyncIterator([raw_image])
            )
        ]

        # Verify response was received
        assert len(responses) == 1
        assert responses[0].outputs[0].correlation_id == "1"

        # Verify transformers were not instantiated
        mock_resizer.assert_not_called()
        mock_compressor.assert_not_called()

        # Verify classify was called
        assert mock_classify.call_count == 1


@pytest.mark.asyncio
async def test_client_transformers_enabled(
    mock_channel: mock.Mock,
    mock_options: AthenaOptions,
) -> None:
    """Test client with image transformers enabled."""
    # Enable transformers in options
    mock_options.resize_images = True
    mock_options.compress_images = True

    test_response = ClassifyResponse(
        outputs=[ClassificationOutput(correlation_id="1")]
    )

    with (
        mock.patch(
            "athena_client.client.athena_client.ClassifierServiceClient"
        ) as mock_client_cls,
        mock.patch(
            "athena_client.client.athena_client.ImageResizer"
        ) as mock_resizer,
        mock.patch(
            "athena_client.client.athena_client.BrotliCompressor"
        ) as mock_compressor,
    ):
        mock_client = mock_client_cls.return_value
        mock_classify = MockAsyncIterator([test_response])
        mock_client.classify = mock_classify

        # Create client with enabled transformers
        client = AthenaClient(mock_channel, mock_options)

        # Send test image that should be resized/compressed
        raw_image = b"uncompressed_test_image"
        responses = [
            response
            async for response in client.classify_images(
                MockAsyncIterator([raw_image])
            )
        ]

        # Verify response was received
        assert len(responses) == 1
        assert responses[0].outputs[0].correlation_id == "1"

        # Verify transformers were instantiated
        mock_resizer.assert_called_once()
        mock_compressor.assert_called_once()

        # Verify classify was called
        assert mock_classify.call_count == 1


@pytest.mark.asyncio
async def test_client_close(
    mock_channel: mock.Mock, mock_options: AthenaOptions
) -> None:
    client = AthenaClient(mock_channel, mock_options)

    await client.close()

    mock_channel.close.assert_called_once()
