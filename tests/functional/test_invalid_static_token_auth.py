import grpc
import pytest
from dotenv import load_dotenv
from grpc.aio import Channel

from resolver_athena_client.client.athena_client import AthenaClient
from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.models.input_model import ImageData
from tests.functional.conftest import get_required_env_var
from tests.utils.image_generation import create_test_image


def create_channel(host: str, token: str) -> Channel:
    credentials = grpc.composite_channel_credentials(
        grpc.ssl_channel_credentials(),
        grpc.access_token_call_credentials(token),
    )
    options = [
        # Keep connections alive longer
        ("grpc.keepalive_time_ms", 60000),  # Send keepalive every 60s
        ("grpc.keepalive_timeout_ms", 30000),  # Wait 30s for keepalive ack
        (
            "grpc.keepalive_permit_without_calls",
            1,
        ),  # Allow keepalive when idle
        # Optimize for persistent streams
        ("grpc.http2.max_pings_without_data", 0),  # Allow unlimited pings
        (
            "grpc.http2.min_time_between_pings_ms",
            60000,
        ),  # Min 60s between pings
        (
            "grpc.http2.min_ping_interval_without_data_ms",
            30000,
        ),  # Min 30s when idle
        # Increase buffer sizes for better performance
        ("grpc.http2.write_buffer_size", 1024 * 1024),  # 1MB write buffer
        (
            "grpc.max_receive_message_length",
            64 * 1024 * 1024,
        ),  # 64MB max message
    ]
    return grpc.aio.secure_channel(host, credentials, options=options)


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
    platform_token = get_required_env_var("ATHENA_TEST_PLATFORM_TOKEN")
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
    platform_token = get_required_env_var("ATHENA_TEST_EXPIRED_TOKEN")
    channel = create_channel(athena_options.host, platform_token)

    async with AthenaClient(channel, athena_options) as client:
        image = ImageData(create_test_image())

        with pytest.raises(grpc.aio.AioRpcError) as exc_info:
            await client.classify_single(image)

        assert exc_info.value.code() == grpc.StatusCode.UNAUTHENTICATED
