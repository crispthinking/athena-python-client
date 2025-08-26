"""Transform image bytes into ClassificationInputs."""

from collections.abc import AsyncIterator

from athena_client.client.correlation import CorrelationProvider
from athena_client.client.transformers.async_transformer import (
    AsyncTransformer,
)
from athena_client.generated.athena.athena_pb2 import (
    ClassificationInput,
    ImageFormat,
    RequestEncoding,
)


class ClassificationInputTransformer(
    AsyncTransformer[bytes, ClassificationInput]
):
    """Transform image bytes into ClassifyRequests."""

    def __init__(
        self,
        source: AsyncIterator[bytes],
        deployment_id: str,
        affiliate: str,
        request_encoding: RequestEncoding.ValueType,
        correlation_provider: type[CorrelationProvider],
    ) -> None:
        """Initialize with source iterator and request configuration.

        Args:
            source: Image bytes source iterator
            deployment_id: Model deployment ID for classification
            affiliate: Affiliate identifier
            request_encoding: Compression type for image bytes
            correlation_provider: Provider for generating correlation IDs

        """
        super().__init__(source)
        self.deployment_id = deployment_id
        self.affiliate = affiliate
        self.request_encoding = request_encoding
        self.correlation_provider = correlation_provider()

    def _create_classification_input(
        self, image_bytes: bytes
    ) -> ClassificationInput:
        # Get image format and data
        return ClassificationInput(
            affiliate=self.affiliate,
            correlation_id=self.correlation_provider.get_correlation_id(
                image_bytes
            ),
            data=image_bytes,
            encoding=self.request_encoding,
            format=ImageFormat.IMAGE_FORMAT_JPEG,
        )

    async def transform(self, data: bytes) -> ClassificationInput:
        """Transform image bytes into a ClassifyRequest."""
        return self._create_classification_input(data)
