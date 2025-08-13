"""Transform image bytes into ClassificationInputs."""

from collections.abc import AsyncIterator

from athena_client.client.transformers.async_transformer import (
    AsyncTransformer,
)
from athena_client.generated.athena.athena_pb2 import (
    ClassificationInput,
    RequestEncoding,
)


class ClassificationInputTransformer(AsyncTransformer[ClassificationInput]):
    """Transform image bytes into ClassifyRequests."""

    def __init__(
        self,
        source: AsyncIterator[bytes],
        deployment_id: str,
        affiliate: str,
        request_encoding: RequestEncoding.ValueType,
    ) -> None:
        """Initialize with source iterator and request configuration.

        Args:
            source: Image bytes source iterator
            deployment_id: Model deployment ID for classification
            affiliate: Affiliate identifier
            correlation_id: Request correlation ID
            request_encoding: Compression type for image bytes

        """
        super().__init__(source)
        self.deployment_id = deployment_id
        self.affiliate = affiliate
        self.request_encoding = request_encoding

    def _create_classification_input(
        self, image_bytes: bytes
    ) -> ClassificationInput:
        # Get image format and data
        return ClassificationInput(
            affiliate=self.affiliate,
            correlation_id="blah",
            data=image_bytes,
            encoding=self.request_encoding,
        )

    async def transform(self, data: bytes) -> ClassificationInput:
        """Transform image bytes into a ClassifyRequest."""
        return self._create_classification_input(data)
