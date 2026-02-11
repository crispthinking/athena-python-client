"""Options object for the Athena client."""

from dataclasses import dataclass

from PIL.Image import Resampling

from resolver_athena_client.client.correlation import (
    CorrelationProvider,
    HashCorrelationProvider,
)


@dataclass
class AthenaOptions:
    """Options for configuring the Athena client behavior.

    This class provides configuration options for controlling how the client
    connects to and interacts with the Athena service.

    Attributes
    ----------
        host: The hostname of the Athena service to connect to.
            Defaults to "localhost".
        resize_images: Whether to automatically resize images before sending.
            When True, images will be resized to the optimal size for the model.
            Defaults to True.
        compress_images: Whether to compress images using Brotli compression.
            Enabling this reduces network bandwidth usage but adds slight CPU
            overhead.
            Defaults to True.
        deployment_id: The ID of the model deployment to use for inference.
            This identifies which model version to use on the server.
            Defaults to "default".
        affiliate: The affiliate ID to associate with requests.
            Used for tracking and billing purposes.
            Defaults to "default".
        max_batch_size: Maximum number of images to batch together in one
            request. Larger batches improve throughput but increase latency.
            Defaults to 100.
        num_workers: Number of concurrent worker tasks for processing images.
            More workers allow parallel processing but use more CPU/memory.
            For CPU-intensive transformations (resize, compression), consider
            setting this to the number of CPU cores. For I/O bound operations,
            higher values may be beneficial. Defaults to 5.
        correlation_provider: Class that generates correlation IDs for requests.
            Used for request tracing and debugging.
            Defaults to HashCorrelationProvider.
        timeout: Optional timeout in seconds for individual gRPC calls.
            When None, uses gRPC default timeouts.
            When set to a float value, individual gRPC requests will timeout
            after that many seconds.
            Defaults to 120.0 seconds.
        keepalive_interval: Optional interval in seconds for sending keepalive
            requests to maintain stream connection. When None, uses a sensible
            default based on server configuration. When set to a float value,
            sends empty requests at this interval to prevent stream timeouts.
            Defaults to None (auto-detect).

    """

    host: str = "localhost"
    resize_images: bool = True
    compress_images: bool = True
    deployment_id: str = "default"
    affiliate: str = "default"
    max_batch_size: int = 10
    num_workers: int = 5
    correlation_provider: type[CorrelationProvider] = HashCorrelationProvider
    timeout: float | None = 120.0
    keepalive_interval: float | None = None
    compression_quality: int = 11  # Brotli quality level (0-11)
    resampling_algorithm: Resampling = Resampling.LANCZOS
