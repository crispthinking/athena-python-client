import os

import pytest
from dotenv import load_dotenv

from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.channel import (
    CredentialHelper,
    create_channel_with_credentials,
)
from resolver_athena_client.client.exceptions import OAuthError


@pytest.mark.asyncio
@pytest.mark.functional
async def test_invalid_secret(athena_options: AthenaOptions) -> None:
    """Test that an invalid OAuth client secret is rejected."""
    load_dotenv()
    invalid_client_secret = "this_is_not_a_valid_secret"
    client_id = os.environ["OAUTH_CLIENT_ID"]
    auth_url = os.getenv(
        "OAUTH_AUTH_URL", "https://crispthinking.auth0.com/oauth/token"
    )
    audience = os.getenv("OAUTH_AUDIENCE", "crisp-athena-live")

    credential_helper = CredentialHelper(
        client_id=client_id,
        client_secret=invalid_client_secret,
        auth_url=auth_url,
        audience=audience,
    )

    with pytest.raises(OAuthError):
        await create_channel_with_credentials(
            athena_options.host, credential_helper=credential_helper
        )


@pytest.mark.asyncio
@pytest.mark.functional
async def test_invalid_clientid(athena_options: AthenaOptions) -> None:
    """Test that an invalid OAuth client secret is rejected."""
    load_dotenv()
    invalid_client_secret = os.environ["OAUTH_CLIENT_SECRET"]
    client_id = "this_is_not_a_valid_client_id"
    auth_url = os.getenv(
        "OAUTH_AUTH_URL", "https://crispthinking.auth0.com/oauth/token"
    )
    audience = os.getenv("OAUTH_AUDIENCE", "crisp-athena-live")

    credential_helper = CredentialHelper(
        client_id=client_id,
        client_secret=invalid_client_secret,
        auth_url=auth_url,
        audience=audience,
    )

    with pytest.raises(OAuthError):
        await create_channel_with_credentials(
            athena_options.host, credential_helper=credential_helper
        )


@pytest.mark.asyncio
@pytest.mark.functional
async def test_invalid_audience(athena_options: AthenaOptions) -> None:
    """Test that an invalid OAuth client secret is rejected."""
    load_dotenv()
    invalid_client_secret = os.environ["OAUTH_CLIENT_SECRET"]
    client_id = "this_is_not_a_valid_client_id"
    auth_url = os.getenv(
        "OAUTH_AUTH_URL", "https://crispthinking.auth0.com/oauth/token"
    )
    audience = "this_is_not_a_valid_audience"

    credential_helper = CredentialHelper(
        client_id=client_id,
        client_secret=invalid_client_secret,
        auth_url=auth_url,
        audience=audience,
    )

    with pytest.raises(OAuthError):
        await create_channel_with_credentials(
            athena_options.host, credential_helper=credential_helper
        )
