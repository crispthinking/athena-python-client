# Athena Client Library

This is a Python library for interacting with the Athena API (Resolver Unknown
CSAM Detection).

## Authentication

The Athena client supports two authentication methods:

### Static Token Authentication
```python
from resolver_athena_client.client.channel import create_channel

# Use a pre-existing authentication token
channel = create_channel(host="your-host", auth_token="your-token")
```

### OAuth Credential Helper (Recommended)
The credential helper automatically handles OAuth token acquisition and refresh:

```python
import asyncio
from resolver_athena_client.client.channel import CredentialHelper, create_channel_with_credentials

async def main():
    # Create credential helper with OAuth settings
    credential_helper = CredentialHelper(
        client_id="your-oauth-client-id",
        client_secret="your-oauth-client-secret",
        auth_url="https://crispthinking.auth0.com/oauth/token",  # Optional, this is default
        audience="crisp-athena-live"  # Optional, this is default
    )

    # Create channel with automatic OAuth handling
    channel = await create_channel_with_credentials(
        host="your-host",
        credential_helper=credential_helper
    )

asyncio.run(main())
```

#### Environment Variables
For the OAuth example to work, set these environment variables:
```bash
export OAUTH_CLIENT_ID="your-client-id"
export OAUTH_CLIENT_SECRET="your-client-secret"
export ATHENA_HOST="your-athena-host"
```

#### OAuth Features
- **Automatic token refresh**: Tokens are automatically refreshed when they expire
- **Thread-safe**: Multiple concurrent requests will safely share cached tokens
- **Error handling**: Comprehensive error handling for OAuth failures
- **Configurable**: Custom OAuth endpoints and audiences supported

See `examples/oauth_example.py` for a complete working example.

## Examples

- `examples/example.py` - Basic classification example with static token
- `examples/oauth_example.py` - OAuth authentication with credential helper
- `examples/create_image.py` - Image generation utilities

## TODO

### Async pipelines
Make pipeline style invocation of the async interators such that we can

async read file -> async transform -> async classify -> async results

### More async pipeline transformers
Add additional pipeline transformers for:
- Image format conversion
- Metadata extraction
- Error recovery and retry



## Development
This package uses [uv](https://docs.astral.sh/uv/) to manage its packages.

To install dependencies, run:

```bash
uv sync --dev
```

To build the package, run:

```bash
uv build
```

To run the standard tests, run:

```bash
pytest -m 'not functional'
```

Developers wishing to run the functional tests should see the
[Functional Tests](#functional-tests) section below.


To lint and format the code, run:

```bash
ruff check
ruff format
```

There are pre-commit hooks that will lint, format, and type check the code.
Install them with:

```bash
pre-commit install
```

To re-compile the protobuf files, run from the repository's root directory:

```bash
bash scripts/compile_proto.sh
```

### Functional Tests
Functional tests require an Athena environment to run against.

#### Pre-Requisites
You will need:
- An Athena host URL.
- An OAuth client ID and secret with access to the Athena environment.
- An affiliate with Athena enabled.
- `imagemagick` installed on your system and on your path at `magick`.


#### Preparing your environment
You can set up the environment variables in a `.env` file in the root of the
repository, or in your shell environment:

You must set the following variables:
```
ATHENA_HOST=your-athena-host (e.g. myathenahost.com)
ATHENA_TEST_AFFILIATE=your-affiliate-id
OAUTH_CLIENT_ID=your-oauth-client-id
OAUTH_CLIENT_SECRET=your-oauth-client-secret
ATHENA_TEST_PLATFORM_TOKEN=a standard platform token - this should be rejected
as only athena specific tokens are accepted.
ATHENA_TEST_EXPIRED_TOKEN=a valid but expired token - this should be rejected.
```

You can optionally set the following variables:
```
OAUTH_AUTH_URL=your-oauth-auth-url (default: https://crispthinking.auth0.com/oauth/token)
OAUTH_AUDIENCE=your-oauth-audience (default: crisp-athena-live)
TEST_IMAGE_COUNT=number-of-images-to-test-with (default: 5000) - this is the
number of images the _streaming_ test will use.
TEST_MIN_INTERVAL=minimum-interval-in-ms (default: None, send as fast as
possible) - this is the minimum interval between
images for the _streaming_ test.
ATHENA_NON_EXISTENT_AFFILIATE=non-existent-affiliate-id (default:
thisaffiliatedoesnotexist123) - this is used to test error handling.
ATHENA_NON_PERMITTED_AFFILIATE=non-permitted-affiliate-id (default:
thisaffiliatedoesnothaveathenaenabled) - this is used to test error handling.
```

Then run the functional tests with:

```bash
pytest -m functional
```
