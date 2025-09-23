import os
import shutil
import subprocess
import uuid

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
from tests.utils.image_generation import create_test_image

SUPPORTED_TEST_FORMATS = [
    "gif",
    "bmp",
    "dib",
    "png",
    "webp",
    "pbm",
    "pgm",
    "ppm",
    "pxm",
    "pnm",
    "sr",
    "ras",
    "tiff",
    "pic",
    "raw_uint8",
]


@pytest_asyncio.fixture
async def credential_helper() -> CredentialHelper:
    load_dotenv()
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
        await credential_helper.get_token()
    except Exception as e:
        msg = "Failed to acquire OAuth token"
        raise AssertionError(msg) from e

    return credential_helper


@pytest.fixture
def athena_options() -> AthenaOptions:
    load_dotenv()
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
    image_format = request.param
    if (magick_path := shutil.which("magick")) is None:
        pytest.fail(
            "ImageMagick 'magick' command not found - cannot run "
            "multi-format test"
        )

    image_dir = tmp_path_factory.mktemp("images")

    base_image_format = "png"
    base_image = create_test_image(
        EXPECTED_WIDTH, EXPECTED_HEIGHT, img_format=base_image_format
    )
    base_image_path = image_dir / "base_image.png"
    if not base_image_path.exists():
        with base_image_path.open("wb") as f:
            f.write(base_image)

    if image_format == base_image_format:
        return base_image

    if image_format == "raw_uint8":
        return create_test_image(
            EXPECTED_WIDTH, EXPECTED_HEIGHT, img_format="raw_uint8"
        )

    image_path = image_dir / f"test_image.{image_format}"
    if not image_path.exists():
        cmd = f'magick "{base_image_path}" "{image_path}"'
        subprocess.run(  # noqa: S603 - false positive :(
            [magick_path, str(base_image_path), str(image_path)],
            check=True,
            shell=False,
        )

        if not image_path.exists():
            pytest.fail(
                f"Failed to create {image_format} image with command: {cmd}"
            )

    with image_path.open("rb") as f:
        return f.read()
