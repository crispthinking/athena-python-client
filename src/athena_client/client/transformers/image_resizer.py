"""Image resizer that ensures all images match expected dimensions."""

import asyncio
from collections.abc import AsyncIterator
from io import BytesIO

from PIL import Image
from PIL.Image import Image as PILImage

from athena_client.client.consts import EXPECTED_HEIGHT, EXPECTED_WIDTH
from athena_client.client.models import ImageData
from athena_client.client.transformers.async_transformer import (
    AsyncTransformer,
)


class ImageResizer(AsyncTransformer[ImageData, ImageData]):
    """Transform ImageData to ensure expected dimensions."""

    def __init__(self, source: AsyncIterator[ImageData]) -> None:
        """Initialize with source iterator and optional size overrides.

        Args:
            source: Iterator yielding ImageData objects

        """
        super().__init__(source)
        self.target_size = (EXPECTED_WIDTH, EXPECTED_HEIGHT)

    def _resize_image(self, image: PILImage) -> PILImage:
        """Resize image to expected dimensions."""
        return image.resize(self.target_size)

    async def transform(self, data: ImageData) -> ImageData:
        """Transform ImageData by resizing to expected dimensions."""

        def process_image() -> bytes:
            with Image.open(BytesIO(data.data)) as image:
                image_to_resize = image

                if image.mode != "RGB":
                    image_to_resize = image.convert("RGB")

                resized = self._resize_image(image_to_resize)

                # Save as PNG to maintain quality and preserve format
                output_buffer = BytesIO()
                resized.save(output_buffer, format="PNG")
                return output_buffer.getvalue()

        resized_bytes = await asyncio.to_thread(process_image)
        # Modify existing ImageData with new bytes and add transformation hashes
        data.data = resized_bytes
        data.add_transformation_hashes()
        return data
