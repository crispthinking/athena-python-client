"""Utility for detecting image formats from raw bytes."""

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


def detect_image_format(data: bytes) -> ImageFormat.ValueType:  # noqa: PLR0911
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

    # Check magic numbers for common image formats
    # PNG: starts with PNG_MAGIC_BYTES
    png_len = len(PNG_MAGIC_BYTES)
    if len(data) >= png_len and data[:png_len] == PNG_MAGIC_BYTES:
        return ImageFormat.IMAGE_FORMAT_PNG

    # JPEG: starts with JPEG_MAGIC_BYTES
    jpeg_len = len(JPEG_MAGIC_BYTES)
    if len(data) >= jpeg_len and data[:jpeg_len] == JPEG_MAGIC_BYTES:
        return ImageFormat.IMAGE_FORMAT_JPEG

    # GIF: starts with GIF87A_MAGIC_BYTES or GIF89A_MAGIC_BYTES
    gif_len = len(GIF87A_MAGIC_BYTES)
    if len(data) >= gif_len and data[:gif_len] in (
        GIF87A_MAGIC_BYTES,
        GIF89A_MAGIC_BYTES,
    ):
        return ImageFormat.IMAGE_FORMAT_GIF

    # BMP: starts with BMP_MAGIC_BYTES
    bmp_len = len(BMP_MAGIC_BYTES)
    if len(data) >= bmp_len and data[:bmp_len] == BMP_MAGIC_BYTES:
        return ImageFormat.IMAGE_FORMAT_BMP

    # WebP: RIFF....WEBP (12 bytes minimum for full signature)
    webp_min_len = len(WEBP_RIFF_MAGIC_BYTES) + len(WEBP_WEBP_MAGIC_BYTES) + 4
    if (
        len(data) >= webp_min_len
        and data[:4] == WEBP_RIFF_MAGIC_BYTES
        and data[8:12] == WEBP_WEBP_MAGIC_BYTES
    ):
        return ImageFormat.IMAGE_FORMAT_WEBP

    # TIFF: little-endian or big-endian magic bytes
    tiff_len = len(TIFF_LE_MAGIC_BYTES)
    if len(data) >= tiff_len and (
        data[:tiff_len] == TIFF_LE_MAGIC_BYTES
        or data[:tiff_len] == TIFF_BE_MAGIC_BYTES
    ):
        return ImageFormat.IMAGE_FORMAT_TIFF

    # Fallback when format cannot be determined
    return ImageFormat.IMAGE_FORMAT_UNSPECIFIED
