"""Utility for detecting image formats from raw bytes."""

from collections.abc import Callable

from resolver_athena_client.generated.athena.models_pb2 import ImageFormat

PNG_MAGIC_BYTES = b"\x89PNG"
JPEG_MAGIC_BYTES = b"\xff\xd8\xff"
GIF87A_MAGIC_BYTES = b"GIF87a"
GIF89A_MAGIC_BYTES = b"GIF89a"
BMP_MAGIC_BYTES = b"BM"
WEBP_RIFF_MAGIC_BYTES = b"RIFF"
WEBP_WEBP_MAGIC_BYTES = b"WEBP"
TIFF_LE_MAGIC_BYTES = b"II*\x00"
TIFF_BE_MAGIC_BYTES = b"MM\x00*"


def _is_webp(data: bytes) -> bool:
    """Check for the RIFF....WEBP signature (12 bytes minimum)."""
    return (
        data[:4] == WEBP_RIFF_MAGIC_BYTES
        and data[8:12] == WEBP_WEBP_MAGIC_BYTES
    )


_ImageFormatDetector = tuple[Callable[[bytes], bool], ImageFormat.ValueType]
_FORMAT_DETECTORS: list[_ImageFormatDetector] = [
    (lambda d: d.startswith(PNG_MAGIC_BYTES), ImageFormat.IMAGE_FORMAT_PNG),
    (lambda d: d.startswith(JPEG_MAGIC_BYTES), ImageFormat.IMAGE_FORMAT_JPEG),
    (
        lambda d: d.startswith((GIF87A_MAGIC_BYTES, GIF89A_MAGIC_BYTES)),
        ImageFormat.IMAGE_FORMAT_GIF,
    ),
    (lambda d: d.startswith(BMP_MAGIC_BYTES), ImageFormat.IMAGE_FORMAT_BMP),
    (_is_webp, ImageFormat.IMAGE_FORMAT_WEBP),
    (
        lambda d: d.startswith((TIFF_LE_MAGIC_BYTES, TIFF_BE_MAGIC_BYTES)),
        ImageFormat.IMAGE_FORMAT_TIFF,
    ),
]


def detect_image_format(data: bytes) -> ImageFormat.ValueType:
    """Detect image format from raw bytes using magic number signatures.

    Args:
    ----
        data: Raw image bytes to analyze

    Returns:
    -------
        ImageFormat enum value representing the detected format

    """
    if not data:
        return ImageFormat.IMAGE_FORMAT_UNSPECIFIED

    for matches, image_format in _FORMAT_DETECTORS:
        if matches(data):
            return image_format

    return ImageFormat.IMAGE_FORMAT_UNSPECIFIED
