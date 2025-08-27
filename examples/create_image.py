"""Random image creation utilities."""

import io
import secrets
from collections.abc import AsyncIterator

from PIL import Image, ImageDraw

from athena_client.client.models import ImageData


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
            secrets.randbits(8),
            secrets.randbits(8),
            secrets.randbits(8),
        ),
    )

    draw = ImageDraw.Draw(image)

    # Draw some random shapes
    for _ in range(3):
        # Random coordinates
        x0 = secrets.randbelow(width)
        y0 = secrets.randbelow(height)
        x1 = secrets.randbelow(width)
        y1 = secrets.randbelow(height)

        # Random color
        color = (
            secrets.randbits(8),
            secrets.randbits(8),
            secrets.randbits(8),
        )

        draw.rectangle(
            [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)], fill=color
        )

    # Convert to JPEG bytes
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format="JPEG")
    return img_byte_arr.getvalue()


async def iter_images(
    max_images: int | None = None, counter: list[int] | None = None
) -> AsyncIterator[ImageData]:
    """Generate random test images.

    Args:
        max_images: Maximum number of images to generate. If None, generates
            infinitely.
        counter: Optional list with single integer to track number of images
            sent.
            The first element will be incremented for each image generated.

    Yields:
        ImageData objects containing JPEG image bytes with random content

    """
    count = 0
    while max_images is None or count < max_images:
        img = create_random_image()
        if counter is not None:
            counter[0] = counter[0] + 1
        yield ImageData(img)
        count += 1
