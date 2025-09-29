"""Transform image bytes into ClassificationInputs."""

from collections.abc import AsyncIterator
from typing import override

from resolver_athena_client.client.correlation import CorrelationProvider
from resolver_athena_client.client.models import ImageData
from resolver_athena_client.client.transformers.async_transformer import (
    AsyncTransformer,
)
from resolver_athena_client.generated.athena.models_pb2 import (
    ClassificationInput,
    ImageFormat,
    RequestEncoding,
)


class ClassificationInputTransformer(
    AsyncTransformer[ImageData, ClassificationInput]
):
    """Transform ImageData into ClassifyRequests."""

    def __init__(
        self,
        source: AsyncIterator[ImageData],
        deployment_id: str,
        affiliate: str,
        request_encoding: RequestEncoding.ValueType,
        correlation_provider: type[CorrelationProvider],
    ) -> None:
        """Initialize with source iterator and request configuration.

        Args:
        ----
            source: ImageData source iterator
            deployment_id: Model deployment ID for classification
            affiliate: Affiliate identifier
            request_encoding: Compression type for image bytes
            correlation_provider: Provider for generating correlation IDs

        """
        super().__init__(source)
        self.deployment_id: str = deployment_id
        self.affiliate: str = affiliate
        self.request_encoding: RequestEncoding.ValueType = request_encoding
        self.correlation_provider: CorrelationProvider = correlation_provider()

    def _create_classification_input(
        self, image_data: ImageData
    ) -> ClassificationInput:
        # Get image format and data
        return ClassificationInput(
            affiliate=self.affiliate,
            correlation_id=self.correlation_provider.get_correlation_id(
                image_data.data
            ),
            data=image_data.data,
            encoding=self.request_encoding,
            format=ImageFormat.IMAGE_FORMAT_RAW_UINT8,
        )

    @override
    async def transform(self, data: ImageData) -> ClassificationInput:
        """Transform ImageData into a ClassifyRequest."""
        return self._create_classification_input(data)
