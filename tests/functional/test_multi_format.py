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
async def test_classsify_single_multi_format(
    athena_options: AthenaOptions,
    credential_helper: CredentialHelper,
    formatted_images: list[tuple[bytes, str]],
) -> None:
    # Create gRPC channel with credentials
    channel = await create_channel_with_credentials(
        athena_options.host, credential_helper
    )

    failed_formats: list[tuple[str, Exception]] = []

    async with AthenaClient(channel, athena_options) as client:
        for img_bytes, img_format in formatted_images:
            try:
                # Create a unique test image for each iteration
                image_data = ImageData(img_bytes)

                # Classify with auto-generated correlation ID
                result = await client.classify_single(image_data)

                if result.error.code:
                    msg = f"Image Result Error: {result.error.message}"
                    pytest.fail(msg)

            except Exception as e:  # noqa: BLE001, PERF203 - its a test.
                failed_formats.append((img_format, e))

    if failed_formats:
        failure_messages = ", ".join(
            [f"{fmt}: {err}" for fmt, err in failed_formats]
        )
        msg = f"Classification failed for formats: {failure_messages}"
        raise AssertionError(msg)
