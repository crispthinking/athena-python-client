"""Utility for detecting image formats from raw bytes."""

from resolver_athena_client.generated.athena.models_pb2 import ImageFormat


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

    # Check magic numbers for common image formats
    # PNG: starts with \x89PNG (need at least 4 bytes)
    if len(data) >= 4 and data[:4] == b"\x89PNG":
        return ImageFormat.IMAGE_FORMAT_PNG

    # JPEG: starts with \xFF\xD8\xFF (need at least 3 bytes)
    if len(data) >= 3 and data[:3] == b"\xFF\xD8\xFF":
        return ImageFormat.IMAGE_FORMAT_JPEG

    # GIF: starts with GIF87a or GIF89a (need at least 6 bytes)
    if len(data) >= 6 and data[:6] in (b"GIF87a", b"GIF89a"):
        return ImageFormat.IMAGE_FORMAT_GIF

    # BMP: starts with BM (need at least 2 bytes)
    if len(data) >= 2 and data[:2] == b"BM":
        return ImageFormat.IMAGE_FORMAT_BMP

    # WebP: starts with RIFF....WEBP (need at least 12 bytes)
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ImageFormat.IMAGE_FORMAT_WEBP

    # TIFF: starts with II* or MM* (need at least 4 bytes)
    if len(data) >= 4 and data[:4] in (b"II*\x00", b"MM\x00*"):
        return ImageFormat.IMAGE_FORMAT_TIFF

    # If we can't detect the format, return UNSPECIFIED
    return ImageFormat.IMAGE_FORMAT_UNSPECIFIED
