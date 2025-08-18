"""Options object for the Athena client."""

from dataclasses import dataclass

from athena_client.client.correlation import (
    CorrelationProvider,
    HashCorrelationProvider,
)


@dataclass
class AthenaOptions:
    """Options for the Athena client."""

    host: str = "localhost"
    resize_images: bool = False
    compress_images: bool = True
    deployment_id: str = "default"
    affiliate: str = "default"
    max_batch_size: int = 100
    correlation_provider: type[CorrelationProvider] = HashCorrelationProvider
