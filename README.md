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

To run the tests, run:

```bash
pytest
```

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
