"""Random image creation utilities."""

import io
import random
from collections.abc import AsyncIterator

from PIL import Image, ImageDraw


def create_random_image(width: int = 640, height: int = 480) -> bytes:
    """Create a random test image with random shapes and colors.

    Args:
        width: Width of the test image in pixels
        height: Height of the test image in pixels

    Returns:
        JPEG image bytes

    """
    # Create a new image with random background color
    image = Image.new(
        "RGB",
        (width, height),
        (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
        ),
    )

    draw = ImageDraw.Draw(image)

    # Draw some random shapes
    for _ in range(3):
        # Random coordinates
        x0 = random.randint(0, width - 1)
        y0 = random.randint(0, height - 1)
        x1 = random.randint(0, width - 1)
        y1 = random.randint(0, height - 1)

        # Random color
        color = (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
        )

        draw.rectangle(
            [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)], fill=color
        )

    # Convert to JPEG bytes
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format="JPEG")
    return img_byte_arr.getvalue()


async def iter_images(max_images: int | None = None) -> AsyncIterator[bytes]:
    """Generate random test images.

    Args:
        max_images: Maximum number of images to generate. If None, generates
        infinitely.

    Yields:
        JPEG image bytes with random content

    """
    count = 0
    while max_images is None or count < max_images:
        yield create_random_image()
        count += 1
