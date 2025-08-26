"""The Athena Client Class."""

import asyncio
import logging
import types
from collections.abc import AsyncIterator

import grpc

from athena_client.client.athena_options import AthenaOptions
from athena_client.client.exceptions import AthenaError
from athena_client.client.transformers.classification_input import (
    ClassificationInputTransformer,
)
from athena_client.client.transformers.jpeg_converter import JpegConverter
from athena_client.client.transformers.request_batcher import RequestBatcher
from athena_client.generated.athena.athena_pb2 import (
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
    """

    def __init__(
        self, channel: grpc.aio.Channel, options: AthenaOptions
    ) -> None:
        """Initialize the Athena Client.

        Args:
            channel: The gRPC channel to use for communication.
            options: Configuration options for the Athena client.

        """
        self.logger = logging.getLogger(__name__)
        self.options = options
        self.channel = channel
        self.classifier = ClassifierServiceClient(self.channel)

    async def classify_images(
        self, images: AsyncIterator[bytes]
    ) -> AsyncIterator[ClassifyResponse]:
        """Classify images using the Athena service.

        Args:
            images: An async iterator of image bytes to classify.

        Returns:
            An async iterator yielding classification responses.

        """
        request_batcher = self._create_request_pipeline(images)

        start_time = asyncio.get_running_loop().time()

        self.logger.info(
            "Starting persistent classification with max timeout: %.1fs",
            self.options.timeout or -1,
        )

        # Single persistent stream with keepalives
        try:
            async for response in self._process_persistent_stream(
                request_batcher, start_time
            ):
                yield response
        finally:
            # Log final stats
            total_duration = asyncio.get_running_loop().time() - start_time
            self.logger.info(
                "Classification completed after %.1fs",
                total_duration,
            )

    def _create_request_pipeline(
        self, images: AsyncIterator[bytes]
    ) -> RequestBatcher:
        """Create the request processing pipeline."""
        image_stream = images

        if self.options.convert_jpeg:
            image_stream = JpegConverter(image_stream)

        input_transformer = ClassificationInputTransformer(
            image_stream,
            deployment_id=self.options.deployment_id,
            affiliate=self.options.affiliate,
            request_encoding=RequestEncoding.REQUEST_ENCODING_UNCOMPRESSED,
            correlation_provider=self.options.correlation_provider,
        )

        return RequestBatcher(
            input_transformer,
            deployment_id=self.options.deployment_id,
            max_batch_size=self.options.max_batch_size,
            keepalive_interval=self.options.keepalive_interval,
        )

    async def _process_persistent_stream(
        self,
        request_batcher: RequestBatcher,
        start_time: float,
    ) -> AsyncIterator[ClassifyResponse]:
        """Process a persistent gRPC stream with keepalives."""
        # Calculate total timeout for the stream
        total_timeout = self.options.timeout

        self.logger.debug(
            "Starting persistent stream (max duration: %.1fs)",
            total_timeout or -1,
        )

        try:
            response_stream = await self.classifier.classify(
                request_batcher, timeout=total_timeout
            )

            async for response in response_stream:
                # Check if we've exceeded our maximum duration
                if self._check_max_duration_reached(start_time):
                    self.logger.debug("Maximum duration reached, ending stream")
                    return

                if response.global_error and response.global_error.message:
                    raise AthenaError(response.global_error.message)

                yield response

        except grpc.aio.AioRpcError as e:
            elapsed = asyncio.get_running_loop().time() - start_time
            self.logger.debug(
                "Persistent stream ended after %.1fs (%s)",
                elapsed,
                self._get_error_code_name(e),
            )
            # Let the stream end naturally - no restarts for persistent streams

    def _check_max_duration_reached(self, start_time: float) -> bool:
        """Check if maximum duration has been reached."""
        if not self.options.timeout:
            return False

        elapsed = asyncio.get_running_loop().time() - start_time
        return elapsed >= self.options.timeout

    def _get_error_code_name(self, error: grpc.aio.AioRpcError) -> str:
        """Get error code name safely."""
        try:
            return error.code().name
        except (AttributeError, TypeError):
            return "UNKNOWN"

    async def close(self) -> None:
        """Close the client and gRPC channel."""
        try:
            await self.channel.close()
        except (grpc.aio.AioRpcError, ConnectionError, OSError) as e:
            self.logger.debug("Error closing channel: %s", str(e))

    async def __aenter__(self) -> "AthenaClient":
        """Context manager entry point."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Context manager exit point."""
        await self.close()
