"""Tests for image format detection."""

import pytest
from resolver_athena_client.generated.athena.models_pb2 import ImageFormat

from resolver_athena_client.client.image_format_detector import (
    detect_image_format,
)


def test_detect_png_format() -> None:
    """Test detection of PNG format."""
    png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    assert detect_image_format(png_header) == ImageFormat.IMAGE_FORMAT_PNG


def test_detect_jpeg_format() -> None:
    """Test detection of JPEG format."""
    jpeg_header = b"\xff\xd8\xff\xe0" + b"\x00" * 100
    assert detect_image_format(jpeg_header) == ImageFormat.IMAGE_FORMAT_JPEG


def test_detect_gif87a_format() -> None:
    """Test detection of GIF87a format."""
    gif_header = b"GIF87a" + b"\x00" * 100
    assert detect_image_format(gif_header) == ImageFormat.IMAGE_FORMAT_GIF


def test_detect_gif89a_format() -> None:
    """Test detection of GIF89a format."""
    gif_header = b"GIF89a" + b"\x00" * 100
    assert detect_image_format(gif_header) == ImageFormat.IMAGE_FORMAT_GIF


def test_detect_bmp_format() -> None:
    """Test detection of BMP format."""
    bmp_header = b"BM" + b"\x00" * 100
    assert detect_image_format(bmp_header) == ImageFormat.IMAGE_FORMAT_BMP


def test_detect_webp_format() -> None:
    """Test detection of WebP format."""
    webp_header = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 100
    assert detect_image_format(webp_header) == ImageFormat.IMAGE_FORMAT_WEBP


def test_detect_tiff_little_endian_format() -> None:
    """Test detection of TIFF format (little-endian)."""
    tiff_header = b"II*\x00" + b"\x00" * 100
    assert detect_image_format(tiff_header) == ImageFormat.IMAGE_FORMAT_TIFF


def test_detect_tiff_big_endian_format() -> None:
    """Test detection of TIFF format (big-endian)."""
    tiff_header = b"MM\x00*" + b"\x00" * 100
    assert detect_image_format(tiff_header) == ImageFormat.IMAGE_FORMAT_TIFF


def test_detect_unspecified_for_empty_data() -> None:
    """Test that empty data returns UNSPECIFIED."""
    assert detect_image_format(b"") == ImageFormat.IMAGE_FORMAT_UNSPECIFIED


def test_detect_unspecified_for_short_data() -> None:
    """Test that very short data returns UNSPECIFIED."""
    assert detect_image_format(b"ab") == ImageFormat.IMAGE_FORMAT_UNSPECIFIED


def test_detect_unspecified_for_unknown_format() -> None:
    """Test that unknown format returns UNSPECIFIED."""
    unknown_data = b"UNKNOWN_FORMAT" + b"\x00" * 100
    assert (
        detect_image_format(unknown_data)
        == ImageFormat.IMAGE_FORMAT_UNSPECIFIED
    )


def test_detect_format_with_real_png_data() -> None:
    """Test detection with minimal valid PNG data."""
    # Minimal PNG: signature + IHDR chunk
    png_data = (
        b"\x89PNG\r\n\x1a\n"  # PNG signature
        b"\x00\x00\x00\x0dIHDR"  # IHDR chunk
        b"\x00\x00\x00\x01"  # width
        b"\x00\x00\x00\x01"  # height
        b"\x08\x02\x00\x00\x00"  # bit depth, color type, etc.
    )
    assert detect_image_format(png_data) == ImageFormat.IMAGE_FORMAT_PNG


def test_detect_format_with_real_jpeg_data() -> None:
    """Test detection with JPEG SOI marker."""
    # JPEG Start of Image (SOI) marker
    jpeg_data = b"\xff\xd8\xff\xdb" + b"\x00" * 100
    assert detect_image_format(jpeg_data) == ImageFormat.IMAGE_FORMAT_JPEG


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (b"\x89PNG\r\n\x1a\n", ImageFormat.IMAGE_FORMAT_PNG),
        (b"\xff\xd8\xff", ImageFormat.IMAGE_FORMAT_JPEG),
        (b"GIF87a", ImageFormat.IMAGE_FORMAT_GIF),
        (b"GIF89a", ImageFormat.IMAGE_FORMAT_GIF),
        (b"BM", ImageFormat.IMAGE_FORMAT_BMP),
        (b"RIFF\x00\x00\x00\x00WEBP", ImageFormat.IMAGE_FORMAT_WEBP),
        (b"II*\x00", ImageFormat.IMAGE_FORMAT_TIFF),
        (b"MM\x00*", ImageFormat.IMAGE_FORMAT_TIFF),
        (b"", ImageFormat.IMAGE_FORMAT_UNSPECIFIED),
        (b"xyz", ImageFormat.IMAGE_FORMAT_UNSPECIFIED),
    ],
)
def test_detect_format_parametrized(
    header: bytes, expected: ImageFormat.ValueType
) -> None:
    """Test format detection with various headers."""
    assert detect_image_format(header) == expected
