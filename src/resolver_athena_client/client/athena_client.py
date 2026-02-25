"""The Athena Client Class."""

import asyncio
import logging
import types
import uuid
from collections.abc import AsyncGenerator, AsyncIterable, AsyncIterator

import grpc
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
from typing_extensions import Self

from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.exceptions import AthenaError
from resolver_athena_client.client.models import ImageData
from resolver_athena_client.client.transformers.core import (
    compress_image,
    resize_image,
)
from resolver_athena_client.client.transformers.worker_batcher import (
    WorkerBatcher,
)
from resolver_athena_client.grpc_wrappers.classifier_service import (
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
        self._active_workers: list[WorkerBatcher[ImageData]] = []

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

        Raises:
        ------
            grpc.aio.AioRpcError: For gRPC communication errors. If the stream
                fails, the error is propagated to the caller rather than being
                retried indefinitely.
            AthenaError: For classification errors from the service.

        Example:
        -------
            # Create ImageData from raw bytes
            image_data = ImageData(image_bytes)
            print(f"Initial hashes: {len(image_data.sha256_hashes)}")  # 1

            async def image_stream():
                yield image_data

            async with AthenaClient(channel, options) as client:
                try:
                    async for response in client.classify_images(
                        image_stream()
                    ):
                        # Process classification response
                        # ImageData will have accumulated transformation hashes
                        pass
                except grpc.aio.AioRpcError as e:
                    # Handle stream failure - client should decide whether to
                    # retry
                    print(f"Stream failed: {e}")

        """
        request_batcher = self._create_request_pipeline(images)

        start_time = asyncio.get_running_loop().time()

        self.logger.debug("Starting persistent classification")

        # Single persistent stream - let WorkerBatcher handle all cancellations
        async for response in self._process_persistent_stream(
            request_batcher, start_time
        ):
            yield response

    async def classify_single(
        self, image_data: ImageData
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
        processed_image = image_data

        # Apply image resizing if enabled
        if self.options.resize_images:
            processed_image = await resize_image(
                processed_image, self.options.resampling_algorithm
            )

        # Apply compression if enabled
        if self.options.compress_images:
            processed_image = compress_image(
                processed_image, self.options.compression_quality
            )

        request_encoding = (
            RequestEncoding.REQUEST_ENCODING_BROTLI
            if self.options.compress_images
            else RequestEncoding.REQUEST_ENCODING_UNCOMPRESSED
        )

        # Ensure we never send UNSPECIFIED format over the API
        # If format is still UNSPECIFIED, default to RAW_UINT8
        image_format = processed_image.image_format
        if image_format == ImageFormat.IMAGE_FORMAT_UNSPECIFIED:
            image_format = ImageFormat.IMAGE_FORMAT_RAW_UINT8_BGR

        classification_input = ClassificationInput(
            affiliate=self.options.affiliate,
            correlation_id=processed_image.correlation_id or str(uuid.uuid4()),
            encoding=request_encoding,
            data=processed_image.data,
            format=image_format,
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
    ) -> WorkerBatcher[ImageData]:
        """Create the request processing pipeline."""
        return self._create_worker_based_pipeline(images)

    def _create_worker_based_pipeline(
        self, images: AsyncIterator[ImageData]
    ) -> WorkerBatcher[ImageData]:
        """Create worker-based pipeline for better concurrency."""

        async def transform_image(image_data: ImageData) -> ClassificationInput:
            """Transform a single image through the full pipeline."""
            # Apply image resizing if enabled
            if self.options.resize_images:
                resized_image = await resize_image(
                    image_data, self.options.resampling_algorithm
                )
            else:
                resized_image = image_data

            # Apply compression if enabled
            if self.options.compress_images:
                compressed_image = compress_image(
                    resized_image, self.options.compression_quality
                )
            else:
                compressed_image = resized_image

            # Set request encoding based on compression setting
            request_encoding = (
                RequestEncoding.REQUEST_ENCODING_BROTLI
                if self.options.compress_images
                else RequestEncoding.REQUEST_ENCODING_UNCOMPRESSED
            )

            # Ensure we never send UNSPECIFIED format over the API
            image_format = compressed_image.image_format
            if image_format == ImageFormat.IMAGE_FORMAT_UNSPECIFIED:
                image_format = ImageFormat.IMAGE_FORMAT_RAW_UINT8_BGR

            if compressed_image.correlation_id:
                correlation_id = compressed_image.correlation_id
            else:
                # Create classification input directly
                correlation_provider = self.options.correlation_provider()
                correlation_id = correlation_provider.get_correlation_id(
                    compressed_image.data
                )

            return ClassificationInput(
                affiliate=self.options.affiliate,
                correlation_id=correlation_id,
                data=compressed_image.data,
                encoding=request_encoding,
                format=image_format,
            )

        worker_batcher = WorkerBatcher(
            source=images,
            transformer_func=transform_image,
            deployment_id=self.options.deployment_id,
            max_batch_size=self.options.max_batch_size,
            num_workers=self.options.num_workers,
            keepalive_interval=self.options.keepalive_interval or 30.0,
        )

        # Track the worker for cleanup
        self._active_workers.append(worker_batcher)

        return worker_batcher

    async def _process_persistent_stream(
        self,
        request_batcher: AsyncIterable[ClassifyRequest],
        start_time: float,
    ) -> AsyncIterator[ClassifyResponse]:
        """Process a gRPC stream without infinite recreation attempts."""
        self.logger.debug("Starting stream")

        try:
            async for response in self._iterate_stream_responses(
                request_batcher
            ):
                yield response
        except asyncio.CancelledError:
            self.logger.debug("Stream cancelled")
            raise
        except grpc.aio.AioRpcError as e:
            elapsed = asyncio.get_running_loop().time() - start_time
            error_code = self._get_error_code_name(e)
            self.logger.exception(
                "gRPC stream error after %.1fs (%s)",
                elapsed,
                error_code,
            )
            raise
        except AthenaError:
            # Re-raise Athena classification errors to caller
            raise
        except Exception:
            elapsed = asyncio.get_running_loop().time() - start_time
            self.logger.exception(
                "Unexpected error in stream after %.1fs", elapsed
            )
            raise

    async def _iterate_stream_responses(
        self,
        request_batcher: AsyncIterable[ClassifyRequest],
    ) -> AsyncIterator[ClassifyResponse]:
        """Iterate over stream responses."""
        # Never apply timeout at gRPC level - handle timeout ourselves
        self.logger.debug("Creating gRPC classify stream...")
        response_stream = await self.classifier.classify(
            request_batcher, timeout=None
        )
        self.logger.debug("gRPC classify stream created successfully")

        self.logger.debug("Starting to iterate over response stream...")
        async for response in response_stream:
            # Log results if we got them
            if response.outputs and len(response.outputs) > 0:
                self.logger.debug(
                    "Received %d results",
                    len(response.outputs),
                )

            if response.global_error and response.global_error.message:
                self._raise_athena_error(response.global_error.message)

            yield response

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
        """Close the client, shutdown active workers, and close gRPC channel."""
        # Shutdown all active workers cleanly
        if self._active_workers:
            self.logger.debug(
                "Shutting down %d active worker batcher(s)",
                len(self._active_workers),
            )

            # Create shutdown tasks for all workers
            async def shutdown_worker(
                worker_batcher: WorkerBatcher[ImageData],
            ) -> None:
                """Safely shutdown a single worker, handling mocks/errors."""
                try:
                    shutdown_method = getattr(worker_batcher, "shutdown", None)
                    if shutdown_method and callable(shutdown_method):
                        shutdown_coro = shutdown_method()
                        # Only await if it's actually a coroutine (not a mock)
                        if asyncio.iscoroutine(shutdown_coro):
                            await shutdown_coro
                        else:
                            # Skip non-coroutine returns (like mocks)
                            self.logger.debug(
                                "Skipping non-coroutine shutdown method"
                            )
                    else:
                        self.logger.debug("Worker has no shutdown method")
                except (AttributeError, TypeError):
                    # Worker doesn't have shutdown method or it's not callable
                    self.logger.debug("Worker shutdown failed, skipping")

            shutdown_tasks = [
                shutdown_worker(worker_batcher)
                for worker_batcher in self._active_workers
            ]

            # Wait for all shutdowns to complete, collecting any errors
            if shutdown_tasks:
                results = await asyncio.gather(
                    *shutdown_tasks, return_exceptions=True
                )
                errors = [
                    str(result)
                    for result in results
                    if isinstance(
                        result,
                        (asyncio.CancelledError, ConnectionError, OSError),
                    )
                ]

                if errors:
                    self.logger.warning(
                        "Errors during worker shutdown: %s",
                        "; ".join(errors),
                    )

            # Clear the list after shutdown
            self._active_workers.clear()
            self.logger.debug("All worker batchers shut down")

        # Close the gRPC channel
        try:
            await self.channel.close()
        except (grpc.aio.AioRpcError, ConnectionError, OSError) as e:
            self.logger.debug("Error closing channel: %s", str(e))

    def _raise_athena_error(self, message: str) -> None:
        """Raise an AthenaError with the given message."""
        raise AthenaError(message)

    async def __aenter__(self) -> Self:
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
