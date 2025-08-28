"""Optimized image resizer that ensures all images match expected dimensions."""

import asyncio
from collections.abc import AsyncIterator
from io import BytesIO

from PIL import Image

from athena_client.client.consts import EXPECTED_HEIGHT, EXPECTED_WIDTH
from athena_client.client.models import ImageData
from athena_client.client.transformers.async_transformer import (
    AsyncTransformer,
)

# Global optimization caches and constants
_MAX_BUFFER_POOL_SIZE = 10
_buffer_pool = []
_target_size = (EXPECTED_WIDTH, EXPECTED_HEIGHT)
_expected_raw_size = EXPECTED_WIDTH * EXPECTED_HEIGHT * 3


def _get_buffer() -> BytesIO:
    """Get a reusable BytesIO buffer from pool."""
    if _buffer_pool:
        buffer = _buffer_pool.pop()
        buffer.seek(0)
        buffer.truncate(0)
        return buffer
    return BytesIO()


def _return_buffer(buffer: BytesIO) -> None:
    """Return buffer to pool for reuse."""
    if len(_buffer_pool) < _MAX_BUFFER_POOL_SIZE:
        _buffer_pool.append(buffer)


def _is_raw_rgb(data: bytes) -> bool:
    """Detect if data is already a raw 448x448x3 RGB array."""
    return (
        len(data) == _expected_raw_size
        and not data.startswith(b"\x89PNG")
        and not data.startswith(b"\xff\xd8\xff")  # JPEG
        and not data.startswith(b"GIF")
        and not data.startswith(b"BM")  # BMP
        and not data.startswith(b"RIFF")  # WebP
    )


class ImageResizer(AsyncTransformer[ImageData, ImageData]):
    """Transform ImageData to ensure expected dimensions with optimization."""

    def __init__(self, source: AsyncIterator[ImageData]) -> None:
        """Initialize with source iterator.

        Args:
            source: Iterator yielding ImageData objects

        """
        super().__init__(source)

    async def transform(self, data: ImageData) -> ImageData:
        """Transform ImageData by resizing to expected dimensions."""

        def process_image() -> bytes:
            # Fast path for raw RGB arrays
            if _is_raw_rgb(data.data):
                # Already correct size raw RGB, convert to PNG efficiently
                image = Image.frombytes("RGB", _target_size, data.data)
                output_buffer = _get_buffer()
                try:
                    image.save(output_buffer, format="PNG", optimize=False)
                    return output_buffer.getvalue()
                finally:
                    _return_buffer(output_buffer)

            # Standard path for encoded images
            input_buffer = BytesIO(data.data)

            with Image.open(input_buffer) as image:
                # Early exit for already-correct images
                if image.size == _target_size and image.mode == "RGB":
                    output_buffer = _get_buffer()
                    try:
                        image.save(output_buffer, format="PNG", optimize=False)
                        return output_buffer.getvalue()
                    finally:
                        _return_buffer(output_buffer)

                # Convert to RGB if needed
                if image.mode != "RGB":
                    rgb_image = image.convert("RGB")
                else:
                    rgb_image = image

                # Resize if needed
                if rgb_image.size != _target_size:
                    resized_image = rgb_image.resize(
                        _target_size, Image.Resampling.LANCZOS
                    )
                else:
                    resized_image = rgb_image

                # Save with optimized settings
                output_buffer = _get_buffer()
                try:
                    resized_image.save(
                        output_buffer, format="PNG", optimize=False
                    )
                    return output_buffer.getvalue()
                finally:
                    _return_buffer(output_buffer)

        # Use thread pool for CPU-intensive processing
        resized_bytes = await asyncio.to_thread(process_image)

        # Modify existing ImageData with new bytes and add transformation hashes
        data.data = resized_bytes
        data.add_transformation_hashes()
        return data
