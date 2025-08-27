from collections.abc import AsyncIterator

import pytest

from athena_client.client.athena_options import AthenaOptions
from athena_client.client.models import ImageData
from athena_client.client.transformers.classification_input import (
    ClassificationInputTransformer,
)
from athena_client.generated.athena.athena_pb2 import RequestEncoding
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
        await anext(transformer)


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
