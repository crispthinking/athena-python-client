import pytest

from resolver_athena_client.client.athena_client import AthenaClient
from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.channel import (
    CredentialHelper,
    create_channel_with_credentials,
)
from resolver_athena_client.client.models import ImageData


@pytest.mark.asyncio
@pytest.mark.functional
async def test_classify_single_multi_format(
    athena_options: AthenaOptions,
    credential_helper: CredentialHelper,
    valid_formatted_image: bytes,
) -> None:
    # Create gRPC channel with credentials
    channel = await create_channel_with_credentials(
        athena_options.host, credential_helper
    )

    async with AthenaClient(channel, athena_options) as client:
        image_data = ImageData(valid_formatted_image)

        # Classify with auto-generated correlation ID
        result = await client.classify_single(image_data)

        if result.error.code:
            msg = f"Image Result Error: {result.error.message}"
            pytest.fail(msg)
