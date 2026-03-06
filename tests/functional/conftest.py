import os
import uuid
from asyncio import Future, Queue, Task, create_task
from collections.abc import AsyncIterator
from copy import deepcopy

import cv2 as cv
import numpy as np
import pytest
import pytest_asyncio
from dotenv import load_dotenv
from grpc.aio import Channel

from resolver_athena_client.client.athena_client import AthenaClient
from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.channel import (
    CredentialHelper,
    create_channel_with_credentials,
)
from resolver_athena_client.client.consts import (
    EXPECTED_HEIGHT,
    EXPECTED_WIDTH,
    MAX_DEPLOYMENT_ID_LENGTH,
)
from resolver_athena_client.client.models.input_model import ImageData
from resolver_athena_client.generated.athena.models_pb2 import (
    ClassificationOutput,
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
    return CredentialHelper(
        client_id=client_id,
        client_secret=client_secret,
        auth_url=auth_url,
        audience=audience,
    )


def _load_options() -> AthenaOptions:
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
        compression_quality=2,
    )


@pytest.fixture
def athena_options() -> AthenaOptions:
    return _load_options()


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


class StreamingSender:
    """Helper class to provide a single-send-like interface with speed

    The class provides a 'send' method that can be passed an imagedata and will
    send it along a stream, and collect all results into an internal buffer.

    The 'send' method will asynchronously wait for the result and return it,
    providing an interface that mimics a single request-response call, while
    under the hood it is using a streaming connection for speed.
    """

    def __init__(self, grpc_channel: Channel, options: AthenaOptions) -> None:
        self._results: list[ClassificationOutput] = []
        self._request_queue: Queue[ImageData] = Queue()
        self._pending_results: dict[str, Future[ClassificationOutput]] = {}

        # tests are run in series, so we gain nothing here from waiting for a
        # batch that will never fill, so just send it immediately for better
        # latency
        streaming_options = deepcopy(options)
        streaming_options.max_batch_size = 1

        self._run_task: Task[None] = create_task(
            self._run(grpc_channel, streaming_options)
        )

    async def _run(self, grpc_channel: Channel, options: AthenaOptions) -> None:
        async with AthenaClient(grpc_channel, options) as client:
            generator = self._send_from_queue()
            responses = client.classify_images(generator)
            async for response in responses:
                for output in response.outputs:
                    if output.correlation_id in self._pending_results:
                        future = self._pending_results.pop(
                            output.correlation_id
                        )
                        future.set_result(output)
                    self._results.append(output)

    async def _send_from_queue(self) -> AsyncIterator[ImageData]:
        """Async generator to yield requests from the queue."""
        while True:
            if image_data := await self._request_queue.get():
                yield image_data
                self._request_queue.task_done()

    async def send(self, image_data: ImageData) -> ClassificationOutput:
        """Send an image and wait for the corresponding result."""
        if self._run_task.done():
            self._run_task.result()

        if image_data.correlation_id is None:
            image_data.correlation_id = str(uuid.uuid4())
        future: Future[ClassificationOutput] = Future()
        self._pending_results[image_data.correlation_id] = future

        await self._request_queue.put(image_data)

        return await future


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def streaming_sender(
    credential_helper: CredentialHelper,
) -> StreamingSender:
    """Fixture to provide a helper for sending over a streaming connection."""
    # Create gRPC channel with credentials
    opts = _load_options()
    channel = await create_channel_with_credentials(
        opts.host, credential_helper
    )
    return StreamingSender(channel, opts)
