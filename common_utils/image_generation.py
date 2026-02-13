"""Ultra-fast random image creation utilities for maximum throughput.

This file is intended to be used for generating benign test images for the
purposes of integration testing the client, as is provided as a convenience
for API consumers.
"""

import asyncio
import random
import time
from collections.abc import AsyncIterator

import cv2 as cv
import numpy as np

from resolver_athena_client.client.models import ImageData

# Global cache for reusable objects and constants
_image_cache: dict[tuple[int, int], np.ndarray] = {}
_rng = random.Random()  # noqa: S311 - Not used for cryptographic purposes


def _get_cached_image(width: int, height: int) -> np.ndarray:
    """Get cached image array, creating if needed."""
    key = (width, height)
    if key not in _image_cache:
        img = np.zeros((height, width, 3), dtype=np.uint8)
        _image_cache[key] = img
    return _image_cache[key]


def create_random_image(
    width: int = 160, height: int = 120, img_format: str = "PNG"
) -> bytes:
    """Create a minimal random image optimized for maximum speed.

    Args:
    ----
        width: Width of the test image in pixels (default: 160)
        height: Height of the test image in pixels (default: 120)
        img_format: Image format (default: PNG)

    Returns:
    -------
        PNG image bytes

    """
    # Get cached image array
    image = _get_cached_image(width, height)
    img = image.copy()

    # Random background color
    bg_r, bg_g, bg_b = (
        _rng.randint(0, 255),
        _rng.randint(0, 255),
        _rng.randint(0, 255),
    )

    # Fill with background color
    img[:, :] = (bg_b, bg_g, bg_r)  # OpenCV uses BGR

    # Add single accent rectangle for visual variation
    accent_color = (255 - bg_b, 255 - bg_g, 255 - bg_r)  # BGR
    x1, y1 = width // 4, height // 4
    x2, y2 = (width * 3) // 4, (height * 3) // 4
    img = cv.rectangle(img, (x1, y1), (x2, y2), accent_color, thickness=-1)

    if img_format.upper() == "RAW_UINT8":
        return img.tobytes()

    # Convert to PNG/JPEG bytes
    ext = f".{img_format.lower()}"
    success, buf = cv.imencode(ext, img)
    if not success:
        err = f"Failed to encode image as {img_format}"
        raise RuntimeError(err)
    return buf.tobytes()


def create_batch_images(
    count: int, width: int = 160, height: int = 120
) -> list[bytes]:
    """Create multiple images in a batch for maximum efficiency.

    Args:
    ----
        count: Number of images to generate
        width: Width of the test images in pixels
        height: Height of the test images in pixels

    Returns:
    -------
        List of PNG image bytes

    """
    images: list[bytes] = []
    image = _get_cached_image(width, height)

    # Pre-calculate accent rectangle coordinates
    x1, y1 = width // 4, height // 4
    x2, y2 = (width * 3) // 4, (height * 3) // 4

    for _ in range(count):
        img = image.copy()
        # Random background
        bg_r, bg_g, bg_b = (
            _rng.randint(0, 255),
            _rng.randint(0, 255),
            _rng.randint(0, 255),
        )
        img[:, :] = (bg_b, bg_g, bg_r)  # OpenCV uses BGR

        # Complement accent color
        accent_color = (255 - bg_b, 255 - bg_g, 255 - bg_r)  # BGR
        img = cv.rectangle(img, (x1, y1), (x2, y2), accent_color, thickness=-1)

        # Convert to PNG bytes
        success, buf = cv.imencode(".png", img)
        if not success:
            msg = "Failed to encode image as PNG"
            raise RuntimeError(msg)
        images.append(buf.tobytes())

    return images


async def iter_images(
    max_images: int | None = None,
) -> AsyncIterator[ImageData]:
    """Generate random test images with maximum throughput optimization.

    Args:
    ----
        max_images: Maximum number of images to generate. If None, generates
            infinitely.

    Yields:
    ------
        ImageData objects containing PNG image bytes with random content

    """
    count = 0
    batch_size = 100  # Large batches for maximum efficiency

    while max_images is None or count < max_images:
        # Calculate batch size for this iteration
        if max_images is not None:
            remaining = max_images - count
            current_batch_size = min(batch_size, remaining)
        else:
            current_batch_size = batch_size

        # Generate batch of images
        images = create_batch_images(current_batch_size, 160, 120)

        # Yield each image
        for img_bytes in images:
            yield ImageData(img_bytes)
            count += 1


def create_test_image(
    width: int = 160,
    height: int = 120,
    seed: int | None = None,
    img_format: str = "PNG",
) -> bytes:
    """Create a test image with specified dimensions and optional seed.

    Args:
    ----
        width: Width of the test image in pixels (default: 160)
        height: Height of the test image in pixels (default: 120)
        seed: Random seed for reproducible images (optional)
        img_format: Image format (e.g., 'PNG', 'JPEG'). PNG and JPEG are
            also supported.

    Returns:
    -------
        image bytes in specified format (default: PNG)

    """
    if seed is not None:
        _rng.seed(seed)

    return create_random_image(width, height, img_format)


async def rate_limited_image_iter(
    min_interval_ms: int,
    max_images: int | None = None,
) -> AsyncIterator[ImageData]:
    """Generate images with a minimum interval between yields."""
    last_yield_time = time.time()
    async for image in iter_images(max_images):
        elapsed_ms = (time.time() - last_yield_time) * 1000
        if elapsed_ms < min_interval_ms:
            await asyncio.sleep((min_interval_ms - elapsed_ms) / 1000)
        yield image
        last_yield_time = time.time()


def create_random_image_generator(
    max_images: int, rate_limit_min_interval_ms: int | None = None
) -> AsyncIterator[ImageData]:
    """Create an async generator for images with optional rate limiting."""
    if rate_limit_min_interval_ms is not None:
        return rate_limited_image_iter(rate_limit_min_interval_ms, max_images)

    return iter_images(max_images)
