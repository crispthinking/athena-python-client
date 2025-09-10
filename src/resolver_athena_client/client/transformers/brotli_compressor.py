"""Compression middleware for images."""

import brotli

from resolver_athena_client.client.models import ImageData
from resolver_athena_client.client.transformers.async_transformer import (
    AsyncTransformer,
)


class BrotliCompressor(AsyncTransformer[ImageData, ImageData]):
    """Middleware for compressing ImageData."""

    async def transform(self, data: ImageData) -> ImageData:
        """Compress the image bytes in ImageData.

        Args:
            data: The ImageData containing bytes to compress.

        Returns:
            ImageData with compressed bytes but original hashes preserved.

        """
        compressed_bytes = brotli.compress(data.data)
        # Modify existing ImageData with compressed bytes but preserve hashes
        # since compression doesn't change image content
        data.data = compressed_bytes
        return data
