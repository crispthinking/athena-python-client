import os
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from dotenv import load_dotenv

from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.channel import CredentialHelper
from tests.utils.image_generation import create_test_image

IMAGEMAGICK_FORMATS = [
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
]


def get_required_env_var(name: str) -> str:
    """Get an environment variable or raise an error if not set."""
    value = os.getenv(name)
    if not value:
        msg = f"Environment variable {name} must be set - cannot run test"
        raise AssertionError(msg)
    return value


@pytest_asyncio.fixture
async def credential_helper() -> CredentialHelper:
    load_dotenv()
    client_id = get_required_env_var("OAUTH_CLIENT_ID")
    client_secret = get_required_env_var("OAUTH_CLIENT_SECRET")
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

    max_deployment_id_length = 63

    deployment_id = f"functional-test-{uuid.uuid4()}"
    if len(deployment_id) > max_deployment_id_length:
        deployment_id = deployment_id[:max_deployment_id_length]

    # Run classification with OAuth authentication
    return AthenaOptions(
        host=host,
        resize_images=True,
        deployment_id=deployment_id,
        compress_images=True,
        timeout=120.0,  # Maximum duration, not forced timeout
        keepalive_interval=30.0,  # Longer intervals for persistent streams
        affiliate="Crisp",
    )


@pytest.fixture
def formatted_images() -> list[tuple[bytes, str]]:
    if (magick_path := shutil.which("magick")) is None:
        msg = (
            "ImageMagick 'magick' command not found - cannot run "
            "multi-format test"
        )
        raise AssertionError(msg)

    images = []
    this_dir = Path(__file__).resolve()
    image_dir = this_dir.parent / "../test_support/images/"

    if not image_dir.exists():
        image_dir.mkdir(parents=True)
    if not image_dir.is_dir():
        msg = f"Image directory {image_dir} is not a directory"
        raise AssertionError(msg)

    base_image_format = "png"
    base_image = create_test_image(448, 448, img_format=base_image_format)
    base_image_path = image_dir / "base_image.png"
    with base_image_path.open("wb") as f:
        f.write(base_image)

    for img_format in IMAGEMAGICK_FORMATS:
        if img_format == base_image_format:
            continue  # base image is already generated.

        converted_image_path = image_dir / f"test_image.{img_format}"
        if converted_image_path.exists():
            continue  # already generated - probably from previous run.

        cmd = f'magick "{base_image_path}" "{converted_image_path}"'
        subprocess.run(  # noqa: S603 - false positive :(
            [magick_path, str(base_image_path), str(converted_image_path)],
            check=True,
            shell=False,
        )

        if not converted_image_path.exists():
            msg = f"Failed to create {img_format} image with command: {cmd}"
            raise AssertionError(msg)

    for path in image_dir.iterdir():
        if path.is_file():
            with path.open("rb") as f:
                img_bytes = f.read()
                images.append((img_bytes, path.suffix.lstrip(".")))

    raw_uint8 = create_test_image(448, 448, img_format="raw_uint8")
    images.append((raw_uint8, "raw_uint8"))
    return images
