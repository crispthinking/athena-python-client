"""Core transformation functions that operate on single ImageData objects.

This module provides the core transformation logic without async iterator
dependencies, making them easier to use for single-item operations and more
composable.
"""

import asyncio
import enum

import brotli
import cv2 as cv
import numpy as np
from resolver_athena_client.generated.athena.models_pb2 import ImageFormat

from resolver_athena_client.client.consts import EXPECTED_HEIGHT, EXPECTED_WIDTH
from resolver_athena_client.client.models import ImageData

# Global optimization constants
_target_size = (EXPECTED_WIDTH, EXPECTED_HEIGHT)
_expected_raw_size = EXPECTED_WIDTH * EXPECTED_HEIGHT * 3


class OpenCVResamplingAlgorithm(enum.Enum):
    """Open CV Resampling Configuration.

    Enum for ease of configuration and type-safety when selecting OpenCV
    resampling algorithms.
    """

    NEAREST = cv.INTER_NEAREST
    BOX = cv.INTER_AREA
    BILINEAR = cv.INTER_LINEAR
    LANCZOS = cv.INTER_LANCZOS4


def _is_raw_bgr_expected_size(data: bytes) -> bool:
    """Detect if data is already a raw BGR array of expected size."""
    return len(data) == _expected_raw_size


async def resize_image(
    image_data: ImageData,
    sampling_algorithm: OpenCVResamplingAlgorithm = (
        OpenCVResamplingAlgorithm.BILINEAR
    ),
) -> ImageData:
    """Resize an image to expected dimensions.

    Args:
    ----
        image_data: The ImageData object to resize
        sampling_algorithm: The resampling algorithm to use for resizing.
            Defaults to LANCZOS.

    Returns:
    -------
        The same ImageData object with resized data (modified in-place)

    """

    def process_image() -> tuple[bytes, bool]:
        # Fast path for raw RGB arrays of correct size
        if _is_raw_bgr_expected_size(image_data.data):
            return image_data.data, False  # No transformation needed

        # Try to load the image data directly
        img_data_buf = np.frombuffer(image_data.data, dtype=np.uint8)
        img = cv.imdecode(img_data_buf, cv.IMREAD_COLOR)

        if img is None:
            err = "Failed to decode image data for resizing"
            raise ValueError(err)

        if img.shape[0] == EXPECTED_HEIGHT and img.shape[1] == EXPECTED_WIDTH:
            resized_img = img
        else:
            resized_img = cv.resize(
                img, _target_size, interpolation=sampling_algorithm.value
            )

        # OpenCV loads in BGR format by default, so we can directly convert to
        # bytes
        return resized_img.tobytes(), True  # Data was transformed

    # Use thread pool for CPU-intensive processing
    resized_bytes, was_transformed = await asyncio.to_thread(process_image)

    # Only modify data and add hashes if transformation occurred
    if was_transformed:
        image_data.data = resized_bytes
        image_data.image_format = ImageFormat.IMAGE_FORMAT_RAW_UINT8_BGR
        image_data.add_transformation_hashes()

    return image_data


def compress_image(image_data: ImageData, quality: int = 11) -> ImageData:
    """Compress image data using Brotli compression.

    Args:
    ----
        image_data: The ImageData object to compress
        quality: Compression quality level (0-11), higher is better compression
            but slower. Default is 11 for maximum compression.

    Returns:
    -------
        The same ImageData object with compressed data (modified in-place)

    """
    compressed_bytes = brotli.compress(image_data.data, quality=quality)
    # Modify existing ImageData with compressed bytes but preserve hashes
    # since compression doesn't change image content
    image_data.data = compressed_bytes
    return image_data
