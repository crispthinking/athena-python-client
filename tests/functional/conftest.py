import os
import uuid

import cv2 as cv
import numpy as np
import pytest
import pytest_asyncio
from dotenv import load_dotenv

from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.channel import CredentialHelper
from resolver_athena_client.client.consts import (
    EXPECTED_HEIGHT,
    EXPECTED_WIDTH,
    MAX_DEPLOYMENT_ID_LENGTH,
)


def _create_base_test_image_opencv(width: int, height: int) -> np.ndarray:
    """Create a test image using only OpenCV2.

    Creates a simple test pattern with background and accent colors.

    Args:
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        numpy array in BGR format suitable for cv.imencode
    """
    # Create a simple test image with random colors
    # Background color (blue-green)
    img_bgr = np.zeros((height, width, 3), dtype=np.uint8)
    img_bgr[:, :] = (100, 150, 200)  # BGR format

    # Add an accent rectangle for visual variation
    x1, y1 = width // 4, height // 4
    x2, y2 = (width * 3) // 4, (height * 3) // 4
    return cv.rectangle(img_bgr, (x1, y1), (x2, y2), (200, 100, 50), -1)


SUPPORTED_TEST_FORMATS = [
    "gif",
    "bmp",
    "dib",
    "png",
    "webp",
    "pbm",
    "pgm",
    "ppm",
    "pnm",
    "sr",
    "ras",
    "tiff",
    "pic",
    "raw_uint8",
    # pxm - OpenCV2 has issues with this format, the docs state it's
    # supported, but pxm is also used to mean PBM/PGM/PPM which are supported,
    # so it's unclear if this format is truly supported.
]


@pytest_asyncio.fixture(scope="session")
async def credential_helper() -> CredentialHelper:
    _ = load_dotenv()
    client_id = os.environ["OAUTH_CLIENT_ID"]
    client_secret = os.environ["OAUTH_CLIENT_SECRET"]
    auth_url = os.getenv(
        "OAUTH_AUTH_URL", "https://crispthinking.auth0.com/oauth/token"
    )
    audience = os.getenv("OAUTH_AUDIENCE", "crisp-athena-live")

    # Create credential helper
    credential_helper = CredentialHelper(
        client_id=client_id,
        client_secret=client_secret,
        auth_url=auth_url,
        audience=audience,
    )

    # Test token acquisition
    try:
        _ = await credential_helper.get_token()
    except Exception as e:
        msg = "Failed to acquire OAuth token"
        raise AssertionError(msg) from e

    return credential_helper


@pytest.fixture
def athena_options() -> AthenaOptions:
    _ = load_dotenv()
    host = os.getenv("ATHENA_HOST", "localhost")

    deployment_id = f"functional-test-{uuid.uuid4()}"
    if len(deployment_id) > MAX_DEPLOYMENT_ID_LENGTH:
        deployment_id = deployment_id[:MAX_DEPLOYMENT_ID_LENGTH]

    affiliate = os.environ["ATHENA_TEST_AFFILIATE"]

    # Run classification with OAuth authentication
    return AthenaOptions(
        host=host,
        resize_images=True,
        deployment_id=deployment_id,
        compress_images=True,
        timeout=120.0,  # Maximum duration, not forced timeout
        keepalive_interval=30.0,  # Longer intervals for persistent streams
        affiliate=affiliate,
    )


@pytest.fixture(scope="session", params=SUPPORTED_TEST_FORMATS)
def valid_formatted_image(
    request: pytest.FixtureRequest,
    tmp_path_factory: pytest.TempPathFactory,
) -> bytes:
    """Generate test images in various formats using OpenCV2.

    Images are cached to disk to avoid regenerating on every test run.
    """
    image_format = request.param
    image_dir = tmp_path_factory.mktemp("images")
    base_image = _create_base_test_image_opencv(EXPECTED_WIDTH, EXPECTED_HEIGHT)

    # Handle raw_uint8 format separately - return raw BGR bytes
    if image_format == "raw_uint8":
        return base_image.tobytes()

    # Check if image already exists in cache
    image_path = image_dir / f"test_image.{image_format}"
    if image_path.exists():
        with image_path.open("rb") as f:
            return f.read()

    # Convert format using OpenCV2 and cache to disk
    # Encode image in the target format
    if image_format in ["pgm", "pbm"]:
        # PGM and PBM are grayscale, so convert the image to grayscale
        gray_image = cv.cvtColor(base_image, cv.COLOR_BGR2GRAY)
        success, encoded = cv.imencode(f".{image_format}", gray_image)
    else:
        success, encoded = cv.imencode(f".{image_format}", base_image)

    if not success:
        pytest.fail(f"OpenCV failed to encode image in {image_format} format")

    image_bytes = encoded.tobytes()

    # Cache the image to disk
    with image_path.open("wb") as f:
        _ = f.write(image_bytes)

    return image_bytes
