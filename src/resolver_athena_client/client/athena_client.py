"""The Athena Client Class."""

import asyncio
import logging
import types
import uuid
from collections.abc import AsyncGenerator, AsyncIterator

import grpc

from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.exceptions import AthenaError
from resolver_athena_client.client.models import ImageData
from resolver_athena_client.client.transformers.brotli_compressor import (
    BrotliCompressor,
)
from resolver_athena_client.client.transformers.classification_input import (
    ClassificationInputTransformer,
)
from resolver_athena_client.client.transformers.core import (
    compress_image,
    resize_image,
)
from resolver_athena_client.client.transformers.image_resizer import (
    ImageResizer,
)
from resolver_athena_client.client.transformers.request_batcher import (
    RequestBatcher,
)
from resolver_athena_client.generated.athena.models_pb2 import (
    ClassificationInput,
    ClassificationOutput,
    ClassifyRequest,
    ClassifyResponse,
    HashType,
    ImageFormat,
    ImageHash,
    RequestEncoding,
)
from resolver_athena_client.grpc_wrappers.classifier_service import (
    ClassifierServiceClient,
)

# Constants
MINIMUM_TIMEOUT_SECONDS = 60.0


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
        ----
            channel: The gRPC channel to use for communication.
            options: Configuration options for the Athena client.

        """
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.options: AthenaOptions = options
        self.channel: grpc.aio.Channel = channel
        self.classifier: ClassifierServiceClient = ClassifierServiceClient(
            self.channel
        )

    async def classify_images(
        self, images: AsyncIterator[ImageData]
    ) -> AsyncIterator[ClassifyResponse]:
        """Classify images using the Athena service.

        Args:
        ----
            images: An async iterator of ImageData objects containing image
                bytes and hash lists tracking transformations. Users must create
                ImageData objects from raw image bytes before passing to this
                method. The transformation pipeline will automatically track
                hash changes for operations that modify visual content (resize,
                format conversion) while preserving hashes for compression
                operations.

        Yields:
        ------
            Classification responses from the service.

        Example:
        -------
            # Create ImageData from raw bytes
            image_data = ImageData(image_bytes)
            print(f"Initial hashes: {len(image_data.sha256_hashes)}")  # 1

            async def image_stream():
                yield image_data

            async with AthenaClient(channel, options) as client:
                async for response in client.classify_images(image_stream()):
                    # Process classification response
                    # ImageData will have accumulated transformation hashes
                    pass

        """
        request_batcher = self._create_request_pipeline(images)

        start_time = asyncio.get_running_loop().time()

        self.logger.info(
            "Starting persistent classification with max timeout: %.1fs",
            self.options.timeout or -1,
        )

        # Single persistent stream with keepalives and reconnection handling
        max_reconnects = 3
        reconnect_count = 0

        while reconnect_count <= max_reconnects:
            try:
                async for response in self._process_persistent_stream(
                    request_batcher, start_time
                ):
                    yield response
                # Stream ended normally, no need to reconnect
                break

            except grpc.aio.AioRpcError as e:
                elapsed = asyncio.get_running_loop().time() - start_time

                if (
                    e.code() == grpc.StatusCode.INTERNAL
                    and "RST_STREAM" in str(e)
                    and reconnect_count < max_reconnects
                ):
                    reconnect_count += 1
                    self.logger.info(
                        "RST_STREAM error after %.1fs, reconnecting "
                        "(attempt %d/%d): %s",
                        elapsed,
                        reconnect_count,
                        max_reconnects,
                        str(e),
                    )

                    # Send empty keepalive request to reopen stream
                    await self._reopen_stream_with_keepalive()
                    continue
                else:
                    # Other gRPC errors or max reconnects reached
                    self.logger.info(
                        "Stream ended after %.1fs (%s), reconnects: %d/%d",
                        elapsed,
                        self._get_error_code_name(e),
                        reconnect_count,
                        max_reconnects,
                    )
                    break

            except Exception:
                raise

        # Log final stats
        total_duration = asyncio.get_running_loop().time() - start_time
        self.logger.info(
            "Classification completed after %.1fs (reconnects: %d/%d)",
            total_duration,
            reconnect_count,
            max_reconnects,
        )

    async def classify_single(
        self, image_data: ImageData, correlation_id: str | None = None
    ) -> ClassificationOutput:
        """Classify a single image synchronously without deployment context.

        This method provides immediate, synchronous classification results for
        single images without requiring deployment coordination, session
        management, or streaming setup. It's ideal for:

        - Low-throughput, low-latency classification scenarios
        - Simple one-off image classifications
        - Applications where immediate responses are preferred over streaming
        - Testing and debugging individual image classifications

        Args:
        ----
            image_data: ImageData object containing image bytes and metadata.
                The image will be processed through the same transformation
                pipeline as the streaming classify method (resize, compression)
                based on client options.
            correlation_id: Optional unique identifier for correlating this
                request. If not provided, a UUID will be generated
                automatically.

        Returns:
        -------
            ClassificationOutput containing either classification results or
            error information for the single image.

        Raises:
        ------
            AthenaError: If the service returns an error.
            grpc.aio.AioRpcError: For gRPC communication errors.

        Example:
        -------
            # Create ImageData from raw bytes
            image_data = ImageData(image_bytes)

            async with AthenaClient(channel, options) as client:
                result = await client.classify_single(image_data)
                if result.error:
                    print(f"Classification error: {result.error.message}")
                else:
                    for classification in result.classifications:
                        print(f"Label: {classification.label}, "
                              f"Weight: {classification.weight}")

        """
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())

        processed_image = image_data

        # Apply image resizing if enabled
        if self.options.resize_images:
            processed_image = await resize_image(processed_image)

        # Apply compression if enabled
        if self.options.compress_images:
            processed_image = compress_image(processed_image)

        request_encoding = (
            RequestEncoding.REQUEST_ENCODING_BROTLI
            if self.options.compress_images
            else RequestEncoding.REQUEST_ENCODING_UNCOMPRESSED
        )

        classification_input = ClassificationInput(
            affiliate=self.options.affiliate,
            correlation_id=correlation_id,
            encoding=request_encoding,
            data=processed_image.data,
            format=ImageFormat.IMAGE_FORMAT_RAW_UINT8,
            hashes=[
                ImageHash(
                    value=hash_value,
                    type=HashType.HASH_TYPE_MD5,
                )
                for hash_value in processed_image.md5_hashes
            ],
        )

        try:
            result = await self.classifier.classify_single(
                classification_input, timeout=self.options.timeout
            )
        except grpc.aio.AioRpcError:
            self.logger.exception(
                "gRPC error in classify_single",
            )
            raise

        # Check for errors in the response
        if result.error and result.error.message:
            self._raise_athena_error(result.error.message)

        return result

    def _create_request_pipeline(
        self, images: AsyncIterator[ImageData]
    ) -> RequestBatcher:
        """Create the request processing pipeline."""
        image_stream = images

        # Apply image resizing if enabled
        if self.options.resize_images:
            image_stream = ImageResizer(image_stream)

        # Apply compression if enabled
        if self.options.compress_images:
            image_stream = BrotliCompressor(image_stream)

        # Set request encoding based on compression setting
        request_encoding = (
            RequestEncoding.REQUEST_ENCODING_BROTLI
            if self.options.compress_images
            else RequestEncoding.REQUEST_ENCODING_UNCOMPRESSED
        )

        input_transformer = ClassificationInputTransformer(
            image_stream,
            deployment_id=self.options.deployment_id,
            affiliate=self.options.affiliate,
            request_encoding=request_encoding,
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
        self.logger.info(
            "Starting persistent stream (max duration: %.1fs)",
            self.options.timeout or -1,
        )

        try:
            # Never apply timeout at gRPC level - handle timeout logic ourselves
            self.logger.debug("Creating gRPC classify stream...")
            response_stream = await self.classifier.classify(
                request_batcher, timeout=None
            )
            self.logger.debug("gRPC classify stream created successfully")

            last_result_time = start_time
            response_count = 0

            self.logger.debug("Starting to iterate over response stream...")
            async for response in response_stream:
                response_count += 1
                current_time = asyncio.get_running_loop().time()

                # Check if this response contains actual results
                has_results = response.outputs and len(response.outputs) > 0

                # If we have results, reset the countdown timer
                if has_results:
                    last_result_time = current_time
                    self.logger.debug(
                        "Received %d results, resetting timeout countdown",
                        len(response.outputs),
                    )

                time_since_last_result = current_time - last_result_time

                should_timeout = (
                    self.options.timeout
                    and time_since_last_result >= self.options.timeout
                    and (current_time - start_time) >= MINIMUM_TIMEOUT_SECONDS
                )

                if should_timeout:
                    self.logger.info(
                        "No results received for %.1fs (timeout=%.1fs)"
                        "closing stream after %.1fs total",
                        time_since_last_result,
                        self.options.timeout,
                        current_time - start_time,
                    )
                    return

                if response.global_error and response.global_error.message:
                    self._raise_athena_error(response.global_error.message)

                yield response

        except grpc.aio.AioRpcError:
            # Re-raise gRPC errors to be handled by outer reconnection logic
            raise
        except Exception:
            elapsed = asyncio.get_running_loop().time() - start_time
            self.logger.exception(
                "Unexpected error in stream after %.1fs", elapsed
            )
            raise

    async def _reopen_stream_with_keepalive(self) -> None:
        """Reopen the stream by sending an empty keepalive request."""
        try:
            # Create an empty keepalive request with just deployment_id
            keepalive_request = ClassifyRequest(
                deployment_id=self.options.deployment_id, inputs=[]
            )

            # Send single keepalive to reestablish connection
            async def keepalive_stream() -> AsyncGenerator[
                ClassifyRequest, None
            ]:
                yield keepalive_request

            # Create new stream with the keepalive
            response_stream = await self.classifier.classify(
                keepalive_stream(), timeout=None
            )

            # Consume one response to establish connection, then close
            async for _ in response_stream:
                break

            self.logger.debug("Stream reopened successfully with keepalive")

        except (grpc.aio.AioRpcError, ConnectionError, OSError) as e:
            self.logger.warning("Failed to reopen stream: %s", str(e))

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

    def _raise_athena_error(self, message: str) -> None:
        """Raise an AthenaError with the given message."""
        raise AthenaError(message)

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
