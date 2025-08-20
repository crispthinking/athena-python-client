"""Module containing input model classes for classification tasks.

This module defines the base input model classes used for image classification
tasks in the Athena client. It provides structured data classes to ensure
consistent input handling across the application.
"""

from dataclasses import dataclass


@dataclass
class ClassificationInput:
    """Base input model for image classification requests.

    Attributes:
        affiliate: The affiliate identifier for the request.
        correlation_id: A unique identifier for tracking the request.
        image_bytes: The raw bytes of the image to be classified.

    """

    affiliate: str
    correlation_id: str
    image_bytes: bytes


class PreSizedInput(ClassificationInput):
    """Classification input for pre-sized images.

    Extends the base ClassificationInput class for images that have already
    been sized according to the model's requirements. This avoids unnecessary
    resizing operations.
    """
