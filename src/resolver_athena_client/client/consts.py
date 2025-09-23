"""Constants for the resolver_athena_client's image properties."""

from typing import Final

# Athena's classifier expects images to be 448x448 pixels.
EXPECTED_WIDTH: Final[int] = 448
EXPECTED_HEIGHT: Final[int] = 448

MAX_DEPLOYMENT_ID_LENGTH: Final[int] = 63
