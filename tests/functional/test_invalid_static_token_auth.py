import os

import grpc
import pytest
from dotenv import load_dotenv
from grpc.aio import Channel

from resolver_athena_client.client.athena_client import AthenaClient
from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.models.input_model import ImageData
from tests.utils.image_generation import create_test_image


def create_channel(host: str, token: str) -> Channel:
    credentials = grpc.composite_channel_credentials(
        grpc.ssl_channel_credentials(),
        grpc.access_token_call_credentials(token),
    )
    return grpc.aio.secure_channel(host, credentials)


@pytest.mark.asyncio
@pytest.mark.functional
async def test_malformed_token_is_rejected(
    athena_options: AthenaOptions,
) -> None:
    """Test that a malformed static token is rejected."""
    malformed_token = "this_is_not_a_valid_token"
    channel = create_channel(athena_options.host, malformed_token)

    async with AthenaClient(channel, athena_options) as client:
        image = ImageData(create_test_image())

        with pytest.raises(grpc.aio.AioRpcError) as exc_info:
            await client.classify_single(image)

        assert exc_info.value.code() == grpc.StatusCode.UNAUTHENTICATED


@pytest.mark.asyncio
@pytest.mark.functional
async def test_platform_token_is_rejected(
    athena_options: AthenaOptions,
) -> None:
    """Test that a standard Resolver platform token is rejected.

    Only static tokens generated for Athena access should be accepted."""
    load_dotenv()
    platform_token = os.environ["ATHENA_TEST_PLATFORM_TOKEN"]
    channel = create_channel(athena_options.host, platform_token)

    async with AthenaClient(channel, athena_options) as client:
        image = ImageData(create_test_image())

        with pytest.raises(grpc.aio.AioRpcError) as exc_info:
            await client.classify_single(image)

        assert exc_info.value.code() == grpc.StatusCode.UNAUTHENTICATED


@pytest.mark.asyncio
@pytest.mark.functional
async def test_expired_token_is_rejected(athena_options: AthenaOptions) -> None:
    """Test that a standard Resolver platform token is rejected.

    Only static tokens generated for Athena access should be accepted."""
    load_dotenv()
    platform_token = os.environ["ATHENA_TEST_EXPIRED_TOKEN"]
    channel = create_channel(athena_options.host, platform_token)

    async with AthenaClient(channel, athena_options) as client:
        image = ImageData(create_test_image())

        with pytest.raises(grpc.aio.AioRpcError) as exc_info:
            await client.classify_single(image)

        assert exc_info.value.code() == grpc.StatusCode.UNAUTHENTICATED
