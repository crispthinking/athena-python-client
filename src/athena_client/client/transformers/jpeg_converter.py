"""JPEG converter transformer for image bytes.

This module provides a transformer that converts input image bytes into JPEG
format with configurable quality settings. This ensures consistent image format
handling throughout the pipeline.
"""

from collections.abc import AsyncIterator
from io import BytesIO

from PIL import Image

from athena_client.client.consts import EXPECTED_HEIGHT, EXPECTED_WIDTH
from athena_client.client.models import ImageData

from .async_transformer import AsyncTransformer

# Constants for JPEG quality settings
DEFAULT_QUALITY = 85
MIN_QUALITY = 1
MAX_QUALITY = 100


class JpegConverter(AsyncTransformer[ImageData, ImageData]):
    """Transformer that converts ImageData to JPEG format.

    This transformer takes ImageData containing image bytes in any PIL-supported
    format and converts them to JPEG format with configurable quality settings.
    This ensures consistent image format handling and can help reduce file size.

    Attributes:
        quality: JPEG quality setting (1-100, default 85)
        optimize: Whether to optimize the JPEG output (default True)

    Example:
        ```python
        async with Client() as client:
            pipeline = JpegConverter(client.process_images())
            async for jpeg_bytes in pipeline:
                print(f"Processed JPEG image: {len(jpeg_bytes)} bytes")
        ```

    """

    def __init__(
        self,
        source: AsyncIterator[ImageData],
        *,
        quality: int = DEFAULT_QUALITY,
        optimize: bool = True,
    ) -> None:
        """Initialize the JPEG converter.

        Args:
            source: Source of ImageData objects
            quality: JPEG quality setting from 1 (worst) to 100 (best).
                Default is 85 which provides good quality with reasonable size.
            optimize: Whether to attempt to optimize the JPEG output.
                Default is True.

        Raises:
            ValueError: If quality is not between 1 and 100.

        """
        super().__init__(source)

        quality_err = "JPEG quality must be between 1 and 100"
        if not MIN_QUALITY <= quality <= MAX_QUALITY:
            raise ValueError(quality_err)

        self.quality = quality
        self.optimize = optimize

    async def transform(self, data: ImageData) -> ImageData:
        """Transform ImageData to JPEG format.

        This method takes ImageData containing image bytes in any PIL-supported
        format and converts them to JPEG format with the configured quality
        settings.

        Args:
            data: ImageData object containing raw image bytes in any
                PIL-supported format.

        Returns:
            ImageData object containing JPEG-formatted image bytes.

        Raises:
            ValueError: If the input bytes cannot be decoded as an image.

        """

        def _raise_empty_data_error() -> None:
            msg = "Empty image data provided"
            raise ValueError(msg)

        def _raise_invalid_format_error() -> None:
            msg = "Input data does not appear to be a valid image format"
            raise ValueError(msg)

        try:
            # Validate input data
            if not data.data:
                _raise_empty_data_error()

            # Try to open the image bytes with PIL
            input_buffer = BytesIO(data.data)
            if input_buffer.getvalue()[:2] not in (
                b"\xff\xd8",
                b"\x89\x50",
                b"\x47\x49",
                b"\x42\x4d",
            ):
                _raise_invalid_format_error()

            with Image.open(input_buffer) as source_img:
                # Convert to RGB if needed (handles RGBA, palette, etc.)
                output_img = source_img
                if source_img.mode in ("RGBA", "LA"):
                    # Convert to RGB, using white background
                    background = Image.new(
                        "RGB", source_img.size, (255, 255, 255)
                    )
                    if source_img.mode == "RGBA":
                        background.paste(source_img, mask=source_img.split()[3])
                    else:
                        background.paste(source_img, mask=source_img.split()[1])
                    output_img = background
                elif source_img.mode != "RGB":
                    output_img = source_img.convert("RGB")

                # Perform resizing and capture the new image
                output_img = output_img.resize(
                    (EXPECTED_WIDTH, EXPECTED_HEIGHT)
                )

                # Save as JPEG to a BytesIO buffer
                buffer = BytesIO()
                output_img.save(
                    buffer,
                    format="JPEG",
                    quality=self.quality,
                    optimize=self.optimize,
                )
                # Modify existing ImageData with new bytes and add hashes
                data.data = buffer.getvalue()
                data.add_transformation_hashes()
                return data

        except Exception as e:
            err_msg = f"Failed to convert image to JPEG: {e}"
            raise ValueError(err_msg) from e
