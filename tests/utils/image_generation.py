"""Ultra-fast random image creation utilities for maximum throughput."""

import io
import random
from collections.abc import AsyncIterator

from PIL import Image, ImageDraw

from resolver_athena_client.client.models import ImageData

# Global cache for reusable objects and constants
_image_cache = {}
_rng = random.Random()  # noqa: S311 - Not used for cryptographic purposes


def _get_cached_image(
    width: int, height: int
) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """Get cached image and draw objects, creating if needed."""
    key = (width, height)
    if key not in _image_cache:
        img = Image.new("RGB", (width, height), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        _image_cache[key] = (img, draw)
    return _image_cache[key]


def create_random_image(
    width: int = 160, height: int = 120, img_format: str = "PNG"
) -> bytes:
    """Create a minimal random image optimized for maximum speed.

    Args:
        width: Width of the test image in pixels (default: 160)
        height: Height of the test image in pixels (default: 120)

    Returns:
        PNG image bytes

    """
    # Get cached image and draw objects
    image, draw = _get_cached_image(width, height)

    # Random background color
    bg_r, bg_g, bg_b = (
        _rng.randint(0, 255),
        _rng.randint(0, 255),
        _rng.randint(0, 255),
    )

    # Fill with background color
    draw.rectangle([0, 0, width, height], fill=(bg_r, bg_g, bg_b))

    # Add single accent rectangle for visual variation
    accent_color = (255 - bg_r, 255 - bg_g, 255 - bg_b)
    x1, y1 = width // 4, height // 4
    x2, y2 = (width * 3) // 4, (height * 3) // 4
    draw.rectangle([x1, y1, x2, y2], fill=accent_color)

    if img_format.upper() == "RAW_UINT8":
        # Return raw bytes
        r_bytes = []
        g_bytes = []
        b_bytes = []
        for y in range(height):
            for x in range(width):
                pixel = image.getpixel((x, y))
                assert pixel is not None
                assert isinstance(pixel, tuple)
                r_bytes.append(pixel[0])
                g_bytes.append(pixel[1])
                b_bytes.append(pixel[2])
        return bytes(r_bytes + g_bytes + b_bytes)

    # Convert to PNG bytes
    buffer = io.BytesIO()
    image.save(buffer, format=img_format)
    return buffer.getvalue()


def create_batch_images(
    count: int, width: int = 160, height: int = 120
) -> list[bytes]:
    """Create multiple images in a batch for maximum efficiency.

    Args:
        count: Number of images to generate
        width: Width of the test images in pixels
        height: Height of the test images in pixels

    Returns:
        List of PNG image bytes

    """
    images = []
    image, draw = _get_cached_image(width, height)

    # Pre-calculate accent rectangle coordinates
    x1, y1 = width // 4, height // 4
    x2, y2 = (width * 3) // 4, (height * 3) // 4

    for _ in range(count):
        # Random background
        bg_r, bg_g, bg_b = (
            _rng.randint(0, 255),
            _rng.randint(0, 255),
            _rng.randint(0, 255),
        )
        draw.rectangle([0, 0, width, height], fill=(bg_r, bg_g, bg_b))

        # Complement accent color
        accent_color = (255 - bg_r, 255 - bg_g, 255 - bg_b)
        draw.rectangle([x1, y1, x2, y2], fill=accent_color)

        # Convert to PNG bytes
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        images.append(buffer.getvalue())

    return images


async def iter_images(
    max_images: int | None = None,
    counter: list[int] | None = None,
) -> AsyncIterator[ImageData]:
    """Generate random test images with maximum throughput optimization.

    Args:
        max_images: Maximum number of images to generate. If None, generates
            infinitely.
        counter: Optional list with single integer to track number of images
            sent.

    Yields:
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
            if counter is not None:
                counter[0] += 1
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
        width: Width of the test image in pixels (default: 160)
        height: Height of the test image in pixels (default: 120)
        seed: Optional seed for reproducible image generation
        img_format: Image format (default: PNG). Other formats like JPEG are
            also supported.

    Returns:
        image bytes in specified format (default: PNG)

    """
    if seed is not None:
        _rng.seed(seed)

    return create_random_image(width, height, img_format)
