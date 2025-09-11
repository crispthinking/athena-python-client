"""Tests for the classify_single method in AthenaClient."""

import io
import uuid
from unittest.mock import AsyncMock, Mock

import grpc.aio
import pytest
from PIL import Image

from resolver_athena_client.client.athena_client import AthenaClient
from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.exceptions import AthenaError
from resolver_athena_client.client.models import ImageData
from resolver_athena_client.generated.athena.models_pb2 import (
    Classification,
    ClassificationError,
    ClassificationInput,
    ClassificationOutput,
    ErrorCode,
    HashType,
    ImageFormat,
    ImageHash,
    RequestEncoding,
)


@pytest.fixture
def athena_options() -> AthenaOptions:
    """Create test AthenaOptions."""
    return AthenaOptions(
        host="localhost:8080",
        affiliate="test-affiliate",
        deployment_id="test-deployment",
        resize_images=False,
        compress_images=False,
        timeout=30.0,
    )


@pytest.fixture
def mock_channel() -> Mock:
    """Create a mock gRPC channel."""
    return Mock()


@pytest.fixture
def mock_classifier() -> Mock:
    """Create a mock classifier service client."""
    return Mock()


@pytest.fixture
def athena_client(
    mock_channel: Mock, athena_options: AthenaOptions, mock_classifier: Mock
) -> AthenaClient:
    """Create AthenaClient with mocked dependencies."""
    client = AthenaClient(mock_channel, athena_options)
    client.classifier = mock_classifier
    return client


@pytest.fixture
def sample_image_data() -> ImageData:
    """Create sample image data for testing."""
    return ImageData(b"fake_image_bytes")


@pytest.mark.asyncio
async def test_classify_single_success(
    athena_client: AthenaClient, sample_image_data: ImageData
) -> None:
    """Test successful single image classification."""
    # Setup mock response
    expected_classification = Classification(label="test_label", weight=0.95)
    mock_output = ClassificationOutput(
        correlation_id="test-correlation",
        classifications=[expected_classification],
    )
    athena_client.classifier.classify_single = AsyncMock(
        return_value=mock_output
    )

    # Call classify_single
    result = await athena_client.classify_single(sample_image_data)

    # Verify result
    assert result == mock_output
    assert len(result.classifications) == 1
    assert result.classifications[0].label == "test_label"
    tolerance = 0.001
    assert abs(result.classifications[0].weight - 0.95) < tolerance
    assert not result.HasField("error")

    # Verify the call was made with correct parameters
    athena_client.classifier.classify_single.assert_called_once()
    call_args = athena_client.classifier.classify_single.call_args[0][0]

    assert isinstance(call_args, ClassificationInput)
    assert call_args.affiliate == "test-affiliate"
    assert call_args.data == b"fake_image_bytes"
    assert call_args.encoding == RequestEncoding.REQUEST_ENCODING_UNCOMPRESSED
    assert call_args.format == ImageFormat.IMAGE_FORMAT_RAW_UINT8
    assert len(call_args.hashes) == 1
    assert call_args.hashes[0].type == HashType.HASH_TYPE_MD5
    assert len(call_args.hashes[0].value) > 0  # MD5 hash should be generated


@pytest.mark.asyncio
async def test_classify_single_with_correlation_id(
    athena_client: AthenaClient, sample_image_data: ImageData
) -> None:
    """Test classify_single with custom correlation ID."""
    custom_correlation_id = "custom-correlation-123"

    # Setup mock response
    mock_output = ClassificationOutput(
        correlation_id=custom_correlation_id,
        classifications=[],
    )
    athena_client.classifier.classify_single = AsyncMock(
        return_value=mock_output
    )

    # Call classify_single with custom correlation ID
    await athena_client.classify_single(
        sample_image_data, correlation_id=custom_correlation_id
    )

    # Verify correlation ID was used
    call_args = athena_client.classifier.classify_single.call_args[0][0]
    assert call_args.correlation_id == custom_correlation_id


@pytest.mark.asyncio
async def test_classify_single_auto_correlation_id(
    athena_client: AthenaClient, sample_image_data: ImageData
) -> None:
    """Test classify_single generates correlation ID when not provided."""
    # Setup mock response
    mock_output = ClassificationOutput(
        correlation_id="auto-generated",
        classifications=[],
    )
    athena_client.classifier.classify_single = AsyncMock(
        return_value=mock_output
    )

    # Call classify_single without correlation ID
    await athena_client.classify_single(sample_image_data)

    # Verify a correlation ID was generated
    call_args = athena_client.classifier.classify_single.call_args[0][0]
    assert call_args.correlation_id is not None
    assert len(call_args.correlation_id) > 0
    # Should be a valid UUID format
    uuid.UUID(call_args.correlation_id)  # This will raise if not a valid UUID


@pytest.mark.asyncio
async def test_classify_single_with_compression(
    athena_client: AthenaClient, sample_image_data: ImageData
) -> None:
    """Test classify_single with compression enabled."""
    # Enable compression
    athena_client.options.compress_images = True

    # Setup mock response
    mock_output = ClassificationOutput(
        correlation_id="test-correlation",
        classifications=[],
    )
    athena_client.classifier.classify_single = AsyncMock(
        return_value=mock_output
    )

    # Call classify_single
    await athena_client.classify_single(sample_image_data)

    # Verify compression settings were applied
    call_args = athena_client.classifier.classify_single.call_args[0][0]
    assert call_args.encoding == RequestEncoding.REQUEST_ENCODING_BROTLI
    # Data should be compressed - check it's the same as the modified image data
    assert call_args.data == sample_image_data.data


@pytest.mark.asyncio
async def test_classify_single_error_handling(
    athena_client: AthenaClient,
) -> None:
    """Test classify_single with image resizing enabled."""
    # Create a simple valid image for testing

    # Create a simple 1x1 pixel image
    img = Image.new("RGB", (1, 1), color="red")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    valid_image_data = ImageData(img_bytes.getvalue())

    # Enable resizing
    athena_client.options.resize_images = True

    # Setup mock response
    mock_output = ClassificationOutput(
        correlation_id="test-correlation",
        classifications=[],
    )
    athena_client.classifier.classify_single = AsyncMock(
        return_value=mock_output
    )

    # Call classify_single with valid image
    await athena_client.classify_single(valid_image_data)

    # Verify resizing was processed (encoding should be uncompressed)
    call_args = athena_client.classifier.classify_single.call_args[0][0]
    assert call_args.encoding == RequestEncoding.REQUEST_ENCODING_UNCOMPRESSED


@pytest.mark.asyncio
async def test_classify_single_with_error_response(
    athena_client: AthenaClient, sample_image_data: ImageData
) -> None:
    """Test classify_single handling error in response."""
    # Setup mock response with error
    error = ClassificationError(
        code=ErrorCode.ERROR_CODE_IMAGE_TOO_LARGE,
        message="Image is too large",
        details="Max size is 10MB",
    )
    mock_output = ClassificationOutput(
        correlation_id="test-correlation",
        classifications=[],
        error=error,
    )
    athena_client.classifier.classify_single = AsyncMock(
        return_value=mock_output
    )

    # Call classify_single and expect AthenaError
    with pytest.raises(AthenaError, match="Image is too large"):
        await athena_client.classify_single(sample_image_data)


@pytest.mark.asyncio
async def test_classify_single_timeout_handling(
    athena_client: AthenaClient, sample_image_data: ImageData
) -> None:
    """Test classify_single handling gRPC errors."""
    # Setup mock to raise gRPC error
    grpc_error = grpc.aio.AioRpcError(
        code=grpc.StatusCode.UNAVAILABLE,
        initial_metadata=grpc.aio.Metadata(),
        trailing_metadata=grpc.aio.Metadata(),
        details="Service unavailable",
    )
    athena_client.classifier.classify_single = AsyncMock(side_effect=grpc_error)

    # Call classify_single and expect gRPC error to be re-raised
    with pytest.raises(grpc.aio.AioRpcError):
        await athena_client.classify_single(sample_image_data)


@pytest.mark.asyncio
async def test_classify_single_timeout_parameter(
    athena_client: AthenaClient, sample_image_data: ImageData
) -> None:
    """Test that timeout is passed to the gRPC call."""
    # Setup mock response
    mock_output = ClassificationOutput(
        correlation_id="test-correlation",
        classifications=[],
    )
    athena_client.classifier.classify_single = AsyncMock(
        return_value=mock_output
    )

    # Call classify_single
    await athena_client.classify_single(sample_image_data)

    # Verify timeout was passed
    call_kwargs = athena_client.classifier.classify_single.call_args[1]
    expected_timeout = 30.0  # From the fixture options
    assert call_kwargs["timeout"] == expected_timeout


@pytest.mark.asyncio
async def test_classify_single_multiple_hashes(
    athena_client: AthenaClient,
) -> None:
    """Test classify_single with multiple transformation hashes."""
    # Create image with multiple transformations
    image_data = ImageData(b"original_image")
    image_data.add_transformation_hashes()  # Simulate a transformation
    image_data.data = b"transformed_image"
    image_data.add_transformation_hashes()  # Another transformation

    # Setup mock response
    mock_output = ClassificationOutput(
        correlation_id="test-correlation",
        classifications=[],
        error=None,
    )
    athena_client.classifier.classify_single = AsyncMock(
        return_value=mock_output
    )

    # Call classify_single
    await athena_client.classify_single(image_data)

    # Verify all hashes were included
    call_args = athena_client.classifier.classify_single.call_args[0][0]
    expected_hash_count = 3  # Original + 2 transformations
    assert len(call_args.hashes) == expected_hash_count
    for hash_obj in call_args.hashes:
        assert isinstance(hash_obj, ImageHash)
        assert hash_obj.type == HashType.HASH_TYPE_MD5
        assert len(hash_obj.value) > 0


@pytest.mark.asyncio
async def test_classify_single_multiple_classifications(
    athena_client: AthenaClient, sample_image_data: ImageData
) -> None:
    """Test classify_single with multiple classification results."""
    # Setup mock response with multiple classifications
    classifications = [
        Classification(label="cat", weight=0.85),
        Classification(label="animal", weight=0.92),
        Classification(label="pet", weight=0.78),
    ]
    mock_output = ClassificationOutput(
        correlation_id="test-correlation",
        classifications=classifications,
    )
    athena_client.classifier.classify_single = AsyncMock(
        return_value=mock_output
    )

    # Call classify_single
    result = await athena_client.classify_single(sample_image_data)

    # Verify all classifications are returned
    expected_classification_count = 3
    assert len(result.classifications) == expected_classification_count
    labels = [c.label for c in result.classifications]
    weights = [c.weight for c in result.classifications]

    assert "cat" in labels
    assert "animal" in labels
    assert "pet" in labels
    tolerance = 0.001
    assert any(abs(w - 0.85) < tolerance for w in weights)
    assert any(abs(w - 0.92) < tolerance for w in weights)
    assert any(abs(w - 0.78) < tolerance for w in weights)


@pytest.mark.asyncio
async def test_classify_single_empty_classifications(
    athena_client: AthenaClient, sample_image_data: ImageData
) -> None:
    """Test classify_single with no classification results."""
    # Setup mock response with empty classifications
    mock_output = ClassificationOutput(
        correlation_id="test-correlation",
        classifications=[],
    )
    athena_client.classifier.classify_single = AsyncMock(
        return_value=mock_output
    )

    # Call classify_single
    result = await athena_client.classify_single(sample_image_data)

    # Verify empty result is handled correctly
    assert len(result.classifications) == 0
    assert not result.HasField("error")  # Check protobuf field is not set
    assert result.correlation_id == "test-correlation"
