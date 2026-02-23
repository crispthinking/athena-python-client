import os

import pytest
from dotenv import load_dotenv

from resolver_athena_client.client.channel import CredentialHelper
from resolver_athena_client.client.exceptions import OAuthError


@pytest.mark.functional
def test_invalid_secret() -> None:
    """Test that an invalid OAuth client secret is rejected."""
    _ = load_dotenv()
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
        _ = credential_helper.get_token()


@pytest.mark.functional
def test_invalid_clientid() -> None:
    """Test that an invalid OAuth client ID is rejected."""
    _ = load_dotenv()
    client_secret = os.environ["OAUTH_CLIENT_SECRET"]
    client_id = "this_is_not_a_valid_client_id"
    auth_url = os.getenv(
        "OAUTH_AUTH_URL", "https://crispthinking.auth0.com/oauth/token"
    )
    audience = os.getenv("OAUTH_AUDIENCE", "crisp-athena-live")

    credential_helper = CredentialHelper(
        client_id=client_id,
        client_secret=client_secret,
        auth_url=auth_url,
        audience=audience,
    )

    with pytest.raises(OAuthError):
        _ = credential_helper.get_token()


@pytest.mark.functional
def test_invalid_audience() -> None:
    """Test that an invalid OAuth audience is rejected."""
    _ = load_dotenv()
    client_secret = os.environ["OAUTH_CLIENT_SECRET"]
    client_id = "this_is_not_a_valid_client_id"
    auth_url = os.getenv(
        "OAUTH_AUTH_URL", "https://crispthinking.auth0.com/oauth/token"
    )
    audience = "this_is_not_a_valid_audience"

    credential_helper = CredentialHelper(
        client_id=client_id,
        client_secret=client_secret,
        auth_url=auth_url,
        audience=audience,
    )

    with pytest.raises(OAuthError):
        _ = credential_helper.get_token()
