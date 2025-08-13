"""Options object for the Athena client."""

from dataclasses import dataclass


@dataclass
class AthenaOptions:
    """Options for the Athena client."""

    host: str = "localhost"
    resize_images: bool = False
    compress_images: bool = True
    deployment_id: str = "default"
    affiliate: str = "default"
    correlation_id: str = "default"
    max_batch_size: int = 100
