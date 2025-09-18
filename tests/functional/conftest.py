import os
import uuid

import pytest
import pytest_asyncio
from dotenv import load_dotenv

from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.channel import CredentialHelper


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
    audience = os.getenv("OAUTH_AUDIENCE", "crisp-athena-dev")

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
