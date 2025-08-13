"""Image resizer that ensures all images match expected dimensions."""

import asyncio
from collections.abc import AsyncIterator
from io import BytesIO

import numpy as np
from PIL import Image
from PIL.Image import Image as PILImage

from athena_client.client.consts import EXPECTED_HEIGHT, EXPECTED_WIDTH
from athena_client.client.transformers.async_transfomer import (
    AsyncTransformer,
)


class ImageResizer(AsyncTransformer[bytes]):
    """Transform image bytes to ensure expected dimensions."""

    def __init__(self, source: AsyncIterator[bytes]) -> None:
        """Initialize with source iterator and optional size overrides.

        Args:
            source: Iterator yielding image bytes

        """
        super().__init__(source)
        self.target_size = (EXPECTED_WIDTH, EXPECTED_HEIGHT)

    def _resize_image(self, image: PILImage) -> PILImage:
        """Resize image to expected dimensions."""
        return image.resize(self.target_size)

    async def transform(self, data: bytes) -> bytes:
        """Transform image bytes by resizing to expected dimensions."""

        def process_image() -> bytes:
            with Image.open(BytesIO(data)) as image:
                image_to_resize = image

                if image.mode != "RGB":
                    image_to_resize = image.convert("RGB")

                resized = self._resize_image(image_to_resize)

                arr = np.array(resized, dtype=np.uint8)
                arr = np.ascontiguousarray(arr)
                return arr.tobytes()

        return await asyncio.to_thread(process_image)
