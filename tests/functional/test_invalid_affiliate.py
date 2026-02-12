import os

import pytest
from dotenv import load_dotenv

from common_utils.image_generation import create_test_image
from resolver_athena_client.client.athena_client import AthenaClient
from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.channel import (
    CredentialHelper,
    create_channel_with_credentials,
)
from resolver_athena_client.client.exceptions import AthenaError
from resolver_athena_client.client.models import ImageData


@pytest.mark.asyncio
@pytest.mark.functional
async def test_non_existent_affiliate(
    athena_options: AthenaOptions, credential_helper: CredentialHelper
) -> None:
    """Functional test for ClassifySingle with non existent affiliate."""

    _ = load_dotenv()

    bad_affiliate = os.getenv(
        "ATHENA_NON_EXISTENT_AFFILIATE", "thisaffiliatedoesnotexist123"
    )

    athena_options.affiliate = bad_affiliate

    # Create gRPC channel with credentials
    channel = await create_channel_with_credentials(
        athena_options.host, credential_helper
    )

    async with AthenaClient(channel, athena_options) as client:
        # Create a unique test image for each iteration
        image_bytes = create_test_image()
        image_data = ImageData(image_bytes)

        # Classify with auto-generated correlation ID
        with pytest.raises(AthenaError) as e:
            _ = await client.classify_single(image_data)

        expected_msg = (
            f"Affiliate ID '{bad_affiliate}' is not permitted "
            "for this client or does not have Athena enabled."
        )
        assert str(e.value) == expected_msg, f"Unexpected error message: {e}"


@pytest.mark.asyncio
@pytest.mark.functional
async def test_existing_not_permitted_affiliate(
    athena_options: AthenaOptions, credential_helper: CredentialHelper
) -> None:
    """Functional test for ClassifySingle with existing but not permitted
    affiliate."""

    _ = load_dotenv()

    bad_affiliate = os.getenv(
        "ATHENA_NON_PERMITTED_AFFILIATE",
        "thisaffiliatedoesnothaveathenaenabled",
    )

    athena_options.affiliate = bad_affiliate

    # Create gRPC channel with credentials
    channel = await create_channel_with_credentials(
        athena_options.host, credential_helper
    )

    async with AthenaClient(channel, athena_options) as client:
        # Create a unique test image for each iteration
        image_bytes = create_test_image()
        image_data = ImageData(image_bytes)

        # Classify with auto-generated correlation ID
        with pytest.raises(AthenaError) as e:
            _ = await client.classify_single(image_data)

        expected_msg = (
            f"Affiliate ID '{bad_affiliate}' is not permitted "
            "for this client or does not have Athena enabled."
        )
        assert str(e.value) == expected_msg, f"Unexpected error message: {e}"
