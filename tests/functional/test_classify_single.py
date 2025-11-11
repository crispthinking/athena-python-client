import pytest

from resolver_athena_client.client.athena_client import AthenaClient
from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.channel import (
    CredentialHelper,
    create_channel_with_credentials,
)
from resolver_athena_client.client.models import ImageData
from tests.utils.image_generation import create_test_image


@pytest.mark.asyncio
@pytest.mark.functional
async def test_classify_single(
    athena_options: AthenaOptions, credential_helper: CredentialHelper
) -> None:
    """Functional test for ClassifySingle endpoint and API methods.

    This test creates a unique test image for each iteration and classifies it.
    The test runs multiple iterations to ensure consistent behavior.
    """

    # Create gRPC channel with credentials
    channel = await create_channel_with_credentials(
        athena_options.host, credential_helper
    )

    async with AthenaClient(channel, athena_options) as client:
        image_bytes = create_test_image()
        image_data = ImageData(image_bytes)

        # Classify with auto-generated correlation ID
        result = await client.classify_single(image_data)

        if result.error.code:
            msg = f"Image Result Error: {result.error.message}"
            pytest.fail(msg)


        found_hash_check = False

        for classification in result.classifications:
            if classification.label.startswith("KnownCSAM-"):
                assert classification.weight == 0.0
                found_hash_check = True
                break

        assert found_hash_check, "No KnownHash- classification found"

        assert [classification for classification in result.classifications
                if classification.label == "UnknownCSAM-Entropy"]

        assert [classification for classification in result.classifications
                if classification.label == "UnknownCSAM-PCSAM"]
