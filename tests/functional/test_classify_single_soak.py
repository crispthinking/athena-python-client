import grpc
import pytest

from common_utils.image_generation import create_test_image
from resolver_athena_client.client.athena_client import AthenaClient
from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.channel import (
    CredentialHelper,
    create_channel_with_credentials,
)
from resolver_athena_client.client.models import ImageData

SOAK_ITERATIONS = 1000
MIN_HASH_CHECK_SUCCESS_RATE = 0.95


@pytest.mark.asyncio
@pytest.mark.functional
@pytest.mark.soak
async def test_classify_single_hash_check_soak(
    athena_options: AthenaOptions, credential_helper: CredentialHelper
) -> None:
    """Soak test: classify images and assert hash check result exists."""

    channel = await create_channel_with_credentials(
        athena_options.host, credential_helper
    )

    async with AthenaClient(channel, athena_options) as client:
        successes = 0
        failures: list[str] = []

        for i in range(SOAK_ITERATIONS):
            image_bytes = create_test_image()
            image_data = ImageData(image_bytes)

            try:
                result = await client.classify_single(image_data)
            except grpc.aio.AioRpcError as e:
                failures.append(
                    f"Iteration {i}: gRPC error {e.code()} - {e.details()}"
                )
                continue

            if result.error.code:
                failures.append(
                    f"Iteration {i}: error {result.error.code}"
                    f" - {result.error.message}"
                )
                continue

            found_hash_check = any(
                c.label.startswith("KnownCSAM-") for c in result.classifications
            )
            if found_hash_check:
                successes += 1
            else:
                failures.append(
                    f"Iteration {i}: no KnownCSAM- classification found"
                )

        success_rate = successes / SOAK_ITERATIONS
        assert success_rate >= MIN_HASH_CHECK_SUCCESS_RATE, (
            f"Hash check success rate {success_rate:.1%} is below 95%. "
            f"{len(failures)} failures:\n" + "\n".join(failures[:20])
        )
