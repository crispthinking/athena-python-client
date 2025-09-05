"""Optimized image resizer that ensures all images match expected dimensions."""

import asyncio
from collections.abc import AsyncIterator
from io import BytesIO

from PIL import Image

from athena_client.client.consts import EXPECTED_HEIGHT, EXPECTED_WIDTH
from athena_client.client.models import ImageData
from athena_client.client.transformers.async_transformer import (
    AsyncTransformer,
)

# Global optimization constants
_target_size = (EXPECTED_WIDTH, EXPECTED_HEIGHT)
_expected_raw_size = EXPECTED_WIDTH * EXPECTED_HEIGHT * 3


def _is_raw_rgb_expected_size(data: bytes) -> bool:
    """Detect if data is already a raw RGB array of expected size."""
    return len(data) == _expected_raw_size


class ImageResizer(AsyncTransformer[ImageData, ImageData]):
    """Transform ImageData to ensure expected dimensions with optimization."""

    def __init__(self, source: AsyncIterator[ImageData]) -> None:
        """Initialize with source iterator.

        Args:
            source: Iterator yielding ImageData objects

        """
        super().__init__(source)

    async def transform(self, data: ImageData) -> ImageData:
        """Transform ImageData by resizing to expected dimensions.

        Converts to raw RGB format (C-order array).

        Returns raw RGB bytes in C-order format (height x width x 3).
        """

        def process_image() -> tuple[bytes, bool]:
            # Fast path for raw RGB arrays of correct size
            if _is_raw_rgb_expected_size(data.data):
                return data.data, False  # No transformation needed

            # Try to load the image data directly
            input_buffer = BytesIO(data.data)

            with Image.open(input_buffer) as image:
                # Convert to RGB if needed
                if image.mode != "RGB":
                    rgb_image = image.convert("RGB")
                else:
                    rgb_image = image

                # Resize if needed
                if rgb_image.size != _target_size:
                    resized_image = rgb_image.resize(
                        _target_size, Image.Resampling.LANCZOS
                    )
                else:
                    resized_image = rgb_image

                # Convert to raw RGB bytes (C-order: height x width x channels)
                return resized_image.tobytes(), True  # Data was transformed

        # Use thread pool for CPU-intensive processing
        resized_bytes, was_transformed = await asyncio.to_thread(process_image)

        # Only modify data and add hashes if transformation occurred
        if was_transformed:
            data.data = resized_bytes
            data.add_transformation_hashes()

        return data
