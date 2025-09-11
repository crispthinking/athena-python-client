"""Core transformation functions that operate on single ImageData objects.

This module provides the core transformation logic without async iterator
dependencies, making them easier to use for single-item operations and more
composable.
"""

import asyncio
from io import BytesIO

import brotli
from PIL import Image

from resolver_athena_client.client.consts import EXPECTED_HEIGHT, EXPECTED_WIDTH
from resolver_athena_client.client.models import ImageData

# Global optimization constants
_target_size = (EXPECTED_WIDTH, EXPECTED_HEIGHT)
_expected_raw_size = EXPECTED_WIDTH * EXPECTED_HEIGHT * 3


def _is_raw_rgb_expected_size(data: bytes) -> bool:
    """Detect if data is already a raw RGB array of expected size."""
    return len(data) == _expected_raw_size


async def resize_image(image_data: ImageData) -> ImageData:
    """Resize an image to expected dimensions.

    Args:
        image_data: The ImageData object to resize

    Returns:
        The same ImageData object with resized data (modified in-place)

    """

    def process_image() -> tuple[bytes, bool]:
        # Fast path for raw RGB arrays of correct size
        if _is_raw_rgb_expected_size(image_data.data):
            return image_data.data, False  # No transformation needed

        # Try to load the image data directly
        input_buffer = BytesIO(image_data.data)

        with Image.open(input_buffer) as image:
            # Convert to RGB if needed
            rgb_image = image.convert("RGB") if image.mode != "RGB" else image

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
        image_data.data = resized_bytes
        image_data.add_transformation_hashes()

    return image_data


def compress_image(image_data: ImageData) -> ImageData:
    """Compress image data using Brotli compression.

    Args:
        image_data: The ImageData object to compress

    Returns:
        The same ImageData object with compressed data (modified in-place)

    """
    compressed_bytes = brotli.compress(image_data.data)
    # Modify existing ImageData with compressed bytes but preserve hashes
    # since compression doesn't change image content
    image_data.data = compressed_bytes
    return image_data
