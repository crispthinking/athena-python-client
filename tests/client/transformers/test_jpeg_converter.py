"""Tests for JPEG converter transformer."""

import asyncio
from collections.abc import AsyncIterator, Sequence
from io import BytesIO

import pytest
from PIL import Image

from athena_client.client.consts import EXPECTED_HEIGHT, EXPECTED_WIDTH
from athena_client.client.transformers.jpeg_converter import JpegConverter


def create_test_image(mode: str, size: tuple[int, int] = (100, 100)) -> bytes:
    """Create a test image with the specified mode and size."""
    img = Image.new(mode, size)
    # Create pattern that compresses differently at different qualities
    for x in range(size[0]):
        for y in range(size[1]):
            img.putpixel((x, y), ((x * 2) % 256,) * (len(mode)))

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


async def create_image_stream(
    images: Sequence[bytes],
) -> AsyncIterator[bytes]:
    """Create an async iterator of image bytes."""
    for img in images:
        yield img
        await asyncio.sleep(0)  # Allow other tasks to run


@pytest.mark.asyncio
async def test_jpeg_converter_basic() -> None:
    """Test basic JPEG conversion with RGB input."""
    input_bytes = create_test_image("RGB")
    converter = JpegConverter(create_image_stream([input_bytes]))

    result = await anext(converter)

    # Verify output is valid JPEG
    with Image.open(BytesIO(result)) as img:
        assert img.format == "JPEG"
        assert img.mode == "RGB"
        assert img.size == (EXPECTED_HEIGHT, EXPECTED_WIDTH)


@pytest.mark.asyncio
async def test_jpeg_converter_rgba() -> None:
    """Test JPEG conversion with RGBA input."""
    input_bytes = create_test_image("RGBA")
    converter = JpegConverter(create_image_stream([input_bytes]))

    result = await anext(converter)

    # Verify RGBA was converted to RGB JPEG
    with Image.open(BytesIO(result)) as img:
        assert img.format == "JPEG"
        assert img.mode == "RGB"  # Should be converted from RGBA


@pytest.mark.asyncio
async def test_jpeg_converter_quality() -> None:
    """Test JPEG conversion with different quality settings."""
    input_bytes = create_test_image("RGB")
    high_quality = JpegConverter(create_image_stream([input_bytes]), quality=95)
    low_quality = JpegConverter(create_image_stream([input_bytes]), quality=10)

    high_result = await anext(high_quality)
    low_result = await anext(low_quality)

    # Lower quality should result in smaller file size
    assert len(low_result) < len(high_result)


@pytest.mark.asyncio
async def test_jpeg_converter_optimize() -> None:
    """Test JPEG conversion with optimization."""
    input_bytes = create_test_image("RGB")
    optimized = JpegConverter(create_image_stream([input_bytes]), optimize=True)
    unoptimized = JpegConverter(
        create_image_stream([input_bytes]),
        optimize=False,
    )

    opt_result = await anext(optimized)
    unopt_result = await anext(unoptimized)

    # Both should produce valid JPEGs
    with Image.open(BytesIO(opt_result)) as img:
        assert img.format == "JPEG"
    with Image.open(BytesIO(unopt_result)) as img:
        assert img.format == "JPEG"


@pytest.mark.asyncio
async def test_jpeg_converter_grayscale() -> None:
    """Test JPEG conversion with grayscale input."""
    input_bytes = create_test_image("L")
    converter = JpegConverter(create_image_stream([input_bytes]))

    result = await anext(converter)

    # Verify grayscale was converted to RGB JPEG
    with Image.open(BytesIO(result)) as img:
        assert img.format == "JPEG"
        assert img.mode == "RGB"


@pytest.mark.asyncio
async def test_jpeg_converter_multiple_images() -> None:
    """Test JPEG conversion with multiple images in stream."""
    images = [
        create_test_image("RGB", (50, 50)),
        create_test_image("RGBA", (100, 100)),
        create_test_image("L", (75, 75)),
    ]
    converter = JpegConverter(create_image_stream(images))

    results = []
    async for result in converter:
        with Image.open(BytesIO(result)) as img:
            assert img.format == "JPEG"
            assert img.mode == "RGB"
            results.append(result)

    assert len(results) == len(images)


def test_jpeg_converter_invalid_quality() -> None:
    """Test JPEG converter with invalid quality settings."""
    msg = "JPEG quality must be between 1 and 100"
    with pytest.raises(ValueError, match=msg):
        JpegConverter(create_image_stream([b""]), quality=0)
    with pytest.raises(ValueError, match=msg):
        JpegConverter(create_image_stream([b""]), quality=101)


@pytest.mark.asyncio
async def test_jpeg_converter_invalid_input() -> None:
    """Test JPEG converter with invalid input bytes."""
    converter = JpegConverter(create_image_stream([b"not an image"]))

    with pytest.raises(ValueError, match="Failed to convert image to JPEG"):
        await anext(converter)
