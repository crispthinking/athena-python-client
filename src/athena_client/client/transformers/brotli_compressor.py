"""Compression middleware for images."""

import brotli

from athena_client.client.transformers.async_transfomer import (
    AsyncTransformer,
)


class BrotliCompressor(AsyncTransformer[bytes]):
    """Middleware for compressing bytes."""

    async def transform(self, data: bytes) -> bytes:
        """Compress the image.

        Args:
            data: The bytes to compress.

        Returns:
            The compressed bytes.

        """
        return brotli.compress(data)
