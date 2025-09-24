"""Compression middleware for images."""

from typing import override

from resolver_athena_client.client.models import ImageData
from resolver_athena_client.client.transformers.async_transformer import (
    AsyncTransformer,
)
from resolver_athena_client.client.transformers.core import compress_image


class BrotliCompressor(AsyncTransformer[ImageData, ImageData]):
    """Middleware for compressing ImageData."""

    @override
    async def transform(self, data: ImageData) -> ImageData:
        """Compress the image bytes in ImageData.

        Args:
        ----
            data: The ImageData containing bytes to compress.

        Returns:
        -------
            ImageData with compressed bytes but original hashes preserved.

        """
        return compress_image(data)
