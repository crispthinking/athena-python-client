import pytest

from common_utils.image_generation import iter_images
from resolver_athena_client.client.athena_client import AthenaClient
from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.channel import (
    CredentialHelper,
    create_channel_with_credentials,
)
from resolver_athena_client.client.deployment_selector import DeploymentSelector


@pytest.mark.asyncio
@pytest.mark.functional
async def test_list_deployments(
    athena_options: AthenaOptions, credential_helper: CredentialHelper
) -> None:
    """Functional test for ListDeployments endpoint and API methods."""

    # Create gRPC channel with credentials
    classify_channel = await create_channel_with_credentials(
        athena_options.host, credential_helper
    )

    async with AthenaClient(classify_channel, athena_options) as client:
        # Classify a few images to ensure at least one deployment exists
        images = iter_images(max_images=32)
        async for _ in client.classify_images(images):
            break  # Only need one response to ensure deployment exists

    deployment_channel = await create_channel_with_credentials(
        athena_options.host, credential_helper
    )

    async with DeploymentSelector(deployment_channel) as deployment_selector:
        try:
            deployments = await deployment_selector.list_deployments()

            if not deployments:
                msg = "No deployments returned"
                pytest.fail(msg)

            if len(deployments.deployments) < 1:
                msg = "Expected at least one deployment"
                pytest.fail(msg)

        except Exception as e:
            msg = "Listing deployments failed"
            raise AssertionError(msg) from e
