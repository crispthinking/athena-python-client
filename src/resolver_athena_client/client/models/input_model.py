"""Module containing input model classes for classification tasks.

This module defines the base input model classes used for image classification
tasks in the Athena client. It provides structured data classes to ensure
consistent input handling across the application.
"""

import hashlib


class ImageData:
    r"""Container for image bytes with calculated hashes.

    This class holds image bytes along with lists of SHA256 and MD5 hashes
    that track all transformations applied to the image. Each transformation
    that modifies the visual content (resize, format conversion) adds a new
    hash to the lists, while operations that don't change visual content
    (compression) preserve the existing hash lists.

    Important: Transformers modify ImageData objects in-place. The same object
    instance is updated with new data and hashes throughout the pipeline,
    maintaining object identity while tracking transformation history.

    Attributes:
    ----------
        data: The raw bytes of the image (modified in-place by transformers).
        sha256_hashes: List of SHA256 hashes tracking image transformations.
            Index 0 is the original image, subsequent indices track
            transformations.
        md5_hashes: List of MD5 hashes tracking image transformations.
            Index 0 is the original image, subsequent indices track
            transformations.

    Example:
    -------
        # Create ImageData from raw bytes
        image_bytes = b"\\x89PNG\\r\\n\\x1a\\n..."  # PNG file bytes
        image_data = ImageData(image_bytes)
        original_id = id(image_data)

        # Access the data and hash lists
        print(f"Image size: {len(image_data.data)} bytes")
        print(f"SHA256 transformations: {image_data.sha256_hashes}")
        print(f"MD5 transformations: {image_data.md5_hashes}")
        print(f"Number of transformations: {len(image_data.sha256_hashes)}")

        # Use with client (transformers modify the same object in-place)
        async def image_stream():
            yield image_data

        async with AthenaClient(channel, options) as client:
            async for response in client.classify_images(image_stream()):
                # Same object identity maintained throughout pipeline
                assert id(image_data) == original_id
                # But hash list has grown to track transformations
                print(f"Final transformations: {len(image_data.sha256_hashes)}")

    """

    def __init__(self, image_bytes: bytes) -> None:
        """Initialize ImageData with bytes and calculate hashes.

        Args:
        ----
            image_bytes: The raw bytes of the image.

        """
        self.data: bytes = image_bytes
        self.sha256_hashes: list[str] = [
            hashlib.sha256(image_bytes).hexdigest()
        ]
        self.md5_hashes: list[str] = [hashlib.md5(image_bytes).hexdigest()]

    def add_transformation_hashes(self) -> None:
        """Add new hashes for the current data to track transformations.

        This method is called by transformers after they modify the image data
        in-place. It should be called after operations that modify the image
        content (resize, format conversion) but not for compression operations
        which preserve visual content.

        The new hashes are calculated from the current data and appended to
        the existing hash lists, maintaining a complete audit trail.
        """
        new_sha256 = hashlib.sha256(self.data).hexdigest()
        new_md5 = hashlib.md5(self.data).hexdigest()
        self.sha256_hashes.append(new_sha256)
        self.md5_hashes.append(new_md5)
