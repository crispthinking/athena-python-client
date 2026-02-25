"""Tests for ImageData model."""

import pytest
from resolver_athena_client.generated.athena.models_pb2 import ImageFormat

from resolver_athena_client.client.models import ImageData


def test_image_data_detects_png_format() -> None:
    """Test that PNG format is detected during initialization."""
    png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    image_data = ImageData(png_data)

    assert image_data.image_format == ImageFormat.IMAGE_FORMAT_PNG
    assert image_data.data == png_data
    assert len(image_data.sha256_hashes) == 1
    assert len(image_data.md5_hashes) == 1


def test_image_data_detects_jpeg_format() -> None:
    """Test that JPEG format is detected during initialization."""
    jpeg_data = b"\xff\xd8\xff\xe0" + b"\x00" * 100
    image_data = ImageData(jpeg_data)

    assert image_data.image_format == ImageFormat.IMAGE_FORMAT_JPEG
    assert image_data.data == jpeg_data


def test_image_data_detects_gif_format() -> None:
    """Test that GIF format is detected during initialization."""
    gif_data = b"GIF89a" + b"\x00" * 100
    image_data = ImageData(gif_data)

    assert image_data.image_format == ImageFormat.IMAGE_FORMAT_GIF


def test_image_data_detects_bmp_format() -> None:
    """Test that BMP format is detected during initialization."""
    bmp_data = b"BM" + b"\x00" * 100
    image_data = ImageData(bmp_data)

    assert image_data.image_format == ImageFormat.IMAGE_FORMAT_BMP


def test_image_data_detects_webp_format() -> None:
    """Test that WebP format is detected during initialization."""
    webp_data = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100
    image_data = ImageData(webp_data)

    assert image_data.image_format == ImageFormat.IMAGE_FORMAT_WEBP


def test_image_data_unspecified_for_unknown_format() -> None:
    """Test that unknown data results in UNSPECIFIED format."""
    unknown_data = b"not_a_valid_image"
    image_data = ImageData(unknown_data)

    assert image_data.image_format == ImageFormat.IMAGE_FORMAT_UNSPECIFIED


def test_image_data_unspecified_for_empty_data() -> None:
    """Test that empty data results in UNSPECIFIED format."""
    image_data = ImageData(b"")

    assert image_data.image_format == ImageFormat.IMAGE_FORMAT_UNSPECIFIED


def test_image_data_transformation_preserves_format() -> None:
    """Test that format is preserved when transformation hashes are added."""
    png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    image_data = ImageData(png_data)

    assert image_data.image_format == ImageFormat.IMAGE_FORMAT_PNG

    # Simulate transformation
    image_data.data = b"transformed_data"
    image_data.add_transformation_hashes()

    # Format should still be PNG (transformers will update it if needed)
    assert image_data.image_format == ImageFormat.IMAGE_FORMAT_PNG
    assert len(image_data.sha256_hashes) == 2  # noqa: PLR2004
    assert len(image_data.md5_hashes) == 2  # noqa: PLR2004


@pytest.mark.parametrize(
    ("data", "expected_format"),
    [
        (b"\x89PNG\r\n\x1a\n", ImageFormat.IMAGE_FORMAT_PNG),
        (b"\xff\xd8\xff", ImageFormat.IMAGE_FORMAT_JPEG),
        (b"GIF87a", ImageFormat.IMAGE_FORMAT_GIF),
        (b"GIF89a", ImageFormat.IMAGE_FORMAT_GIF),
        (b"BM", ImageFormat.IMAGE_FORMAT_BMP),
        (b"RIFF\x00\x00\x00\x00WEBP", ImageFormat.IMAGE_FORMAT_WEBP),
        (b"II*\x00", ImageFormat.IMAGE_FORMAT_TIFF),
        (b"MM\x00*", ImageFormat.IMAGE_FORMAT_TIFF),
        (b"unknown", ImageFormat.IMAGE_FORMAT_UNSPECIFIED),
        (b"", ImageFormat.IMAGE_FORMAT_UNSPECIFIED),
    ],
)
def test_image_data_format_detection_parametrized(
    data: bytes, expected_format: ImageFormat.ValueType
) -> None:
    """Test format detection with various image data."""
    image_data = ImageData(data)
    assert image_data.image_format == expected_format
