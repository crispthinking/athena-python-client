"""The Athena Client Class."""

import types
from collections.abc import AsyncIterator

import grpc

from athena_client.client.athena_options import AthenaOptions
from athena_client.client.exceptions import AthenaError
from athena_client.client.transformers.brotli_compressor import BrotliCompressor
from athena_client.client.transformers.classification_input import (
    ClassificationInputTransformer,
)
from athena_client.client.transformers.image_resizer import ImageResizer
from athena_client.client.transformers.request_batcher import RequestBatcher
from athena_client.generated.athena.athena_pb2 import (
    ClassifyRequest,
    ClassifyResponse,
    RequestEncoding,
)
from athena_client.grpc_wrappers.classifier_service import (
    ClassifierServiceClient,
)


class AthenaClient:
    """The Athena Client Class.

    This class provides coroutine methods for interacting with the
    Athena service.

    Attributes:
        options (AthenaOptions): Configuration options for the Athena client.

    """

    def __init__(
        self, channel: grpc.aio.Channel, options: AthenaOptions
    ) -> None:
        """Initialize the Athena Client.

        Args:
            channel (grpc.aio.Channel): The gRPC channel to use for
                communication.
            options (AthenaOptions): Configuration options for the
                Athena client.

        """
        self.options = options
        self.channel = channel
        self.classifier = ClassifierServiceClient(self.channel)
        self.deployment_id = options.deployment_id
        self.max_batch_size = options.max_batch_size

    async def classify_images(
        self, images: AsyncIterator[bytes]
    ) -> AsyncIterator[ClassifyResponse]:
        """Classify an image using the Athena service.

        Args:
            images (AsyncIterator[Image]): The images to classify in an
                asynchronous iterator.

        Returns:
            AsyncIterator[ClassifyResponse]: An async iterator yielding
                classification responses from the server.

        """
        # Build middleware pipeline
        image_stream = images

        if self.options.resize_images:
            image_stream = ImageResizer(image_stream)

        if self.options.compress_images:
            image_stream = BrotliCompressor(image_stream)

        input_transformer = ClassificationInputTransformer(
            image_stream,
            deployment_id=self.options.deployment_id,
            affiliate=self.options.affiliate,
            request_encoding=RequestEncoding.REQUEST_ENCODING_BROTLI,
            correlation_provider=self.options.correlation_provider,
        )

        request_batcher = RequestBatcher(
            input_transformer,
            deployment_id=self.deployment_id,
            max_batch_size=self.max_batch_size,
        )

        # Stream responses directly from the classifier
        async for response in await self.classifier.classify(request_batcher):
            if response.global_error and response.global_error.message:
                raise AthenaError(response.global_error.message)
            yield response

    async def close(self) -> None:
        """Close the client and GRPC channel."""
        await self.channel.close()

    async def __aenter__(self) -> "AthenaClient":
        """Context manager entrypoint.

        Registers the client with the server by sending a
        classification request. With a deployment ID.
        """
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Context manager exit."""
        await self.close()

    @staticmethod
    async def _init_request_generator(
        deployment_id: str,
    ) -> AsyncIterator[ClassifyRequest]:
        yield ClassifyRequest(deployment_id=deployment_id)
