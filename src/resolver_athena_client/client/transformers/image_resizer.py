"""Optimized image resizer that ensures all images match expected dimensions."""

from collections.abc import AsyncIterator
from typing import override

from resolver_athena_client.client.models import ImageData
from resolver_athena_client.client.transformers.async_transformer import (
    AsyncTransformer,
)
from resolver_athena_client.client.transformers.core import resize_image


class ImageResizer(AsyncTransformer[ImageData, ImageData]):
    """Transform ImageData to ensure expected dimensions with optimization."""

    def __init__(self, source: AsyncIterator[ImageData]) -> None:
        """Initialize with source iterator.

        Args:
        ----
            source: Iterator yielding ImageData objects

        """
        super().__init__(source)

    @override
    async def transform(self, data: ImageData) -> ImageData:
        """Transform ImageData by resizing to expected dimensions.

        Converts to raw RGB format (C-order array).

        Returns raw RGB bytes in C-order format (height x width x 3).
        """
        return await resize_image(data)
