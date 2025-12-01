from collections.abc import AsyncIterator

import pytest

from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.models import ImageData
from resolver_athena_client.client.transformers.classification_input import (
    ClassificationInputTransformer,
)
from resolver_athena_client.generated.athena.models_pb2 import (
    ImageFormat,
    RequestEncoding,
)
from tests.utils.mock_async_iterator import MockAsyncIterator


@pytest.fixture
def source() -> AsyncIterator[ImageData]:
    test_data = [ImageData(b"test1"), ImageData(b"test2"), ImageData(b"test3")]
    return MockAsyncIterator(test_data)


@pytest.fixture
def transformer_config() -> AthenaOptions:
    return AthenaOptions(
        deployment_id="test-deployment",
        affiliate="test-affiliate",
    )


@pytest.mark.asyncio
async def test_classification_input_transform(
    transformer_config: AthenaOptions,
) -> None:
    transformer = ClassificationInputTransformer(
        source=MockAsyncIterator([]),
        deployment_id=transformer_config.deployment_id,
        affiliate=transformer_config.affiliate,
        request_encoding=RequestEncoding.REQUEST_ENCODING_BROTLI,
        correlation_provider=transformer_config.correlation_provider,
    )

    test_data = ImageData(b"test image bytes")
    result = await transformer.transform(test_data)

    assert result.affiliate == transformer_config.affiliate
    assert isinstance(
        result.correlation_id, str
    )  # Should be a non-empty string
    assert result.data == test_data.data
    assert result.encoding == RequestEncoding.REQUEST_ENCODING_BROTLI
    # UNSPECIFIED should be converted to RAW_UINT8 before sending
    assert result.format == ImageFormat.IMAGE_FORMAT_RAW_UINT8


@pytest.mark.asyncio
async def test_classification_input_iteration(
    source: AsyncIterator[ImageData], transformer_config: AthenaOptions
) -> None:
    transformer = ClassificationInputTransformer(
        source=source,
        deployment_id=transformer_config.deployment_id,
        affiliate=transformer_config.affiliate,
        request_encoding=RequestEncoding.REQUEST_ENCODING_BROTLI,
        correlation_provider=transformer_config.correlation_provider,
    )

    # Test first item
    result = await anext(transformer)
    assert result.data == b"test1"
    assert result.affiliate == transformer_config.affiliate
    assert result.encoding == RequestEncoding.REQUEST_ENCODING_BROTLI
    # UNSPECIFIED should be converted to RAW_UINT8 before sending
    assert result.format == ImageFormat.IMAGE_FORMAT_RAW_UINT8

    # Test second item
    result = await anext(transformer)
    assert result.data == b"test2"
    assert result.affiliate == transformer_config.affiliate
    assert result.encoding == RequestEncoding.REQUEST_ENCODING_BROTLI

    # Test third item
    result = await anext(transformer)
    assert result.data == b"test3"
    assert result.affiliate == transformer_config.affiliate
    assert result.encoding == RequestEncoding.REQUEST_ENCODING_BROTLI

    # Test StopAsyncIteration
    with pytest.raises(StopAsyncIteration):
        _ = await anext(transformer)


@pytest.mark.asyncio
async def test_classification_input_empty(
    transformer_config: AthenaOptions,
) -> None:
    """Test ClassificationInputTransformer with empty input."""
    transformer = ClassificationInputTransformer(
        source=MockAsyncIterator([]),
        deployment_id=transformer_config.deployment_id,
        affiliate=transformer_config.affiliate,
        request_encoding=RequestEncoding.REQUEST_ENCODING_BROTLI,
        correlation_provider=transformer_config.correlation_provider,
    )

    test_data = ImageData(b"")
    result = await transformer.transform(test_data)
    assert result.data == b""
    assert result.affiliate == transformer_config.affiliate
    assert result.encoding == RequestEncoding.REQUEST_ENCODING_BROTLI
    # UNSPECIFIED should be converted to RAW_UINT8 before sending
    assert result.format == ImageFormat.IMAGE_FORMAT_RAW_UINT8


@pytest.mark.parametrize(
    "encoding",
    [
        RequestEncoding.REQUEST_ENCODING_UNSPECIFIED,
        RequestEncoding.REQUEST_ENCODING_UNCOMPRESSED,
        RequestEncoding.REQUEST_ENCODING_BROTLI,
    ],
)
@pytest.mark.asyncio
async def test_classification_input_encodings(
    encoding: RequestEncoding.ValueType, transformer_config: AthenaOptions
) -> None:
    """Test ClassificationInputTransformer with different encodings."""
    transformer = ClassificationInputTransformer(
        source=MockAsyncIterator([]),
        deployment_id=transformer_config.deployment_id,
        affiliate=transformer_config.affiliate,
        request_encoding=encoding,
        correlation_provider=transformer_config.correlation_provider,
    )

    test_data = ImageData(b"test")
    result = await transformer.transform(test_data)
    assert result.encoding == encoding
    # UNSPECIFIED should be converted to RAW_UINT8 before sending
    assert result.format == ImageFormat.IMAGE_FORMAT_RAW_UINT8


@pytest.mark.asyncio
async def test_classification_input_preserves_detected_format(
    transformer_config: AthenaOptions,
) -> None:
    """Test that detected image formats are preserved and sent correctly."""
    transformer = ClassificationInputTransformer(
        source=MockAsyncIterator([]),
        deployment_id=transformer_config.deployment_id,
        affiliate=transformer_config.affiliate,
        request_encoding=RequestEncoding.REQUEST_ENCODING_BROTLI,
        correlation_provider=transformer_config.correlation_provider,
    )

    # Create ImageData with PNG header - should be detected as PNG
    png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    test_data = ImageData(png_data)
    result = await transformer.transform(test_data)

    # PNG format should be preserved
    assert result.format == ImageFormat.IMAGE_FORMAT_PNG
    assert result.data == png_data


@pytest.mark.asyncio
async def test_classification_input_never_sends_unspecified(
    transformer_config: AthenaOptions,
) -> None:
    """Test that UNSPECIFIED format is never sent over the API."""
    transformer = ClassificationInputTransformer(
        source=MockAsyncIterator([]),
        deployment_id=transformer_config.deployment_id,
        affiliate=transformer_config.affiliate,
        request_encoding=RequestEncoding.REQUEST_ENCODING_BROTLI,
        correlation_provider=transformer_config.correlation_provider,
    )

    # Test with various unrecognizable data that would be UNSPECIFIED
    test_cases = [
        b"random_bytes",
        b"xyz",
        b"\x00\x00\x00\x00",
        b"not_an_image",
    ]

    for data in test_cases:
        test_data = ImageData(data)
        result = await transformer.transform(test_data)
        # Should never be UNSPECIFIED - defaults to RAW_UINT8
        assert result.format != ImageFormat.IMAGE_FORMAT_UNSPECIFIED
        assert result.format == ImageFormat.IMAGE_FORMAT_RAW_UINT8
