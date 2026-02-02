Authentication
==============

The Athena Client library supports multiple authentication methods to accommodate different use cases and security requirements. This guide covers setup and usage for each method.

Authentication Methods
----------------------

OAuth Credential Helper (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The OAuth credential helper is the recommended authentication method for production applications. It provides automatic token management, refresh capabilities, and robust error handling.

**Features:**
* Automatic token acquisition and refresh
* Thread-safe token caching
* Comprehensive error handling
* Configurable OAuth endpoints
* Secure credential management

**Setup:**

.. code-block:: python

    from resolver_athena_client.client.channel import CredentialHelper, create_channel_with_credentials

    # Create credential helper
    credential_helper = CredentialHelper(
        client_id="your-oauth-client-id",
        client_secret="your-oauth-client-secret",
        auth_url="https://crispthinking.auth0.com/oauth/token",  # Optional
        audience="crisp-athena-live"  # Optional
    )

    # Create authenticated channel
    channel = await create_channel_with_credentials(
        host="your-athena-host",
        credential_helper=credential_helper
    )

**Environment Variables:**

Set these environment variables for OAuth authentication:

.. code-block:: bash

    # Required
    export OAUTH_CLIENT_ID="your-client-id"
    export OAUTH_CLIENT_SECRET="your-client-secret"
    export ATHENA_HOST="your-athena-host"

    # Optional (defaults shown)
    export OAUTH_AUTH_URL="https://crispthinking.auth0.com/oauth/token"
    export OAUTH_AUDIENCE="crisp-athena-live"

**Complete Example:**

.. code-block:: python

    import asyncio
    import os
    from dotenv import load_dotenv

    from resolver_athena_client.client.channel import CredentialHelper, create_channel_with_credentials
    from resolver_athena_client.client.athena_client import AthenaClient
    from resolver_athena_client.client.athena_options import AthenaOptions

    async def main():
        load_dotenv()

        # OAuth configuration from environment
        credential_helper = CredentialHelper(
            client_id=os.getenv("OAUTH_CLIENT_ID"),
            client_secret=os.getenv("OAUTH_CLIENT_SECRET"),
            auth_url=os.getenv("OAUTH_AUTH_URL", "https://crispthinking.auth0.com/oauth/token"),
            audience=os.getenv("OAUTH_AUDIENCE", "crisp-athena-live"),
        )

        # Create authenticated channel
        channel = await create_channel_with_credentials(
            host=os.getenv("ATHENA_HOST"),
            credential_helper=credential_helper
        )

        options = AthenaOptions(
            host=os.getenv("ATHENA_HOST"),
            deployment_id="your-deployment-id",
            resize_images=True,
            compress_images=True,
            affiliate="your-affiliate",
        )

        async with AthenaClient(channel, options) as client:
            # Your classification logic here
            pass

    asyncio.run(main())

Static Token Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Static token authentication is suitable for simple use cases or when you already have a valid authentication token.

**Features:**
* Simple setup with existing tokens
* No automatic token refresh
* Suitable for short-lived operations
* Lower overhead for simple scripts

**Setup:**

.. code-block:: python

    from resolver_athena_client.client.channel import create_channel

    # Use existing authentication token
    channel = create_channel(
        host="your-athena-host",
        auth_token="your-static-token"
    )

**Complete Example:**

.. code-block:: python

    import asyncio
    from resolver_athena_client.client.channel import create_channel
    from resolver_athena_client.client.athena_client import AthenaClient
    from resolver_athena_client.client.athena_options import AthenaOptions

    async def main():
        # Create channel with static token
        channel = create_channel(
            host="your-athena-host",
            auth_token="your-static-token"
        )

        options = AthenaOptions(
            host="your-athena-host",
            deployment_id="your-deployment-id",
            resize_images=True,
            compress_images=True,
            affiliate="your-affiliate",
        )

        async with AthenaClient(channel, options) as client:
            # Your classification logic here
            pass

    asyncio.run(main())

OAuth Configuration
-------------------

Default Endpoints
~~~~~~~~~~~~~~~~~

The credential helper uses these default OAuth endpoints:

* **Auth URL**: ``https://crispthinking.auth0.com/oauth/token``
* **Audience**: ``crisp-athena-live``

These can be overridden when creating the ``CredentialHelper``.

Custom OAuth Endpoints
~~~~~~~~~~~~~~~~~~~~~~

For custom OAuth providers or different environments:

.. code-block:: python

    credential_helper = CredentialHelper(
        client_id="your-client-id",
        client_secret="your-client-secret",
        auth_url="https://your-custom-auth-provider.com/oauth/token",
        audience="your-custom-audience"
    )

Token Management
~~~~~~~~~~~~~~~~

The credential helper automatically manages tokens:

* **Acquisition**: Tokens are acquired on first use
* **Caching**: Valid tokens are cached to avoid unnecessary requests
* **Refresh**: Tokens are automatically refreshed before expiration
* **Thread Safety**: Multiple concurrent requests safely share cached tokens

Security Best Practices
------------------------

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

Always use environment variables for sensitive credentials:

.. code-block:: bash

    # .env file
    OAUTH_CLIENT_ID=your-client-id
    OAUTH_CLIENT_SECRET=your-client-secret
    ATHENA_HOST=your-athena-host

**Never hardcode credentials** in your source code.

Credential Storage
~~~~~~~~~~~~~~~~~~

For production applications:

* Use secure credential storage (e.g., AWS Secrets Manager, Azure Key Vault)
* Rotate credentials regularly
* Use least-privilege access policies
* Monitor credential usage

Development vs Production
~~~~~~~~~~~~~~~~~~~~~~~~~

**Development:**

.. code-block:: python

    # Development configuration
    credential_helper = CredentialHelper(
        client_id=os.getenv("DEV_OAUTH_CLIENT_ID"),
        client_secret=os.getenv("DEV_OAUTH_CLIENT_SECRET"),
        auth_url="https://dev-auth.example.com/oauth/token",
        audience="dev-athena"
    )

**Production:**

.. code-block:: python

    # Production configuration with secure credential retrieval
    credential_helper = CredentialHelper(
        client_id=get_secret("PROD_OAUTH_CLIENT_ID"),
        client_secret=get_secret("PROD_OAUTH_CLIENT_SECRET"),
        auth_url="https://auth.example.com/oauth/token",
        audience="prod-athena"
    )

Error Handling
--------------

OAuth Errors
~~~~~~~~~~~~

Handle OAuth-specific errors gracefully:

.. code-block:: python

    from resolver_athena_client.client.exceptions import AuthenticationError

    try:
        token = credential_helper.get_token()
    except AuthenticationError as e:
        logger.error(f"OAuth authentication failed: {e}")
        # Handle authentication failure
    except Exception as e:
        logger.error(f"Unexpected error during authentication: {e}")
        # Handle other errors

Connection Errors
~~~~~~~~~~~~~~~~~

Handle connection-related authentication issues:

.. code-block:: python

    try:
        channel = await create_channel_with_credentials(host, credential_helper)
    except ConnectionError as e:
        logger.error(f"Failed to connect to Athena service: {e}")
        # Handle connection failure
    except AuthenticationError as e:
        logger.error(f"Authentication failed: {e}")
        # Handle authentication failure

Token Refresh Errors
~~~~~~~~~~~~~~~~~~~~~

The credential helper automatically handles token refresh, but you can monitor for issues:

.. code-block:: python

    import logging

    # Enable debug logging to see token refresh activity
    logging.getLogger("athena_client.client.channel").setLevel(logging.DEBUG)

    async with AthenaClient(channel, options) as client:
        # Long-running operations will automatically refresh tokens as needed
        pass

Troubleshooting
---------------

Common Authentication Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**"Invalid client credentials"**:
   * Verify ``OAUTH_CLIENT_ID`` and ``OAUTH_CLIENT_SECRET`` are correct
   * Check that credentials haven't been revoked
   * Ensure you're using the correct auth URL

**"Invalid audience"**:
   * Verify the audience parameter matches your OAuth configuration
   * Check with your OAuth provider for the correct audience value

**"Token expired"**:
   * The credential helper should automatically refresh tokens
   * If this persists, check your OAuth provider's token lifetime settings

**Connection timeouts**:
   * Verify the ``ATHENA_HOST`` is correct and accessible
   * Check network connectivity
   * Ensure the service is running and accepting connections

Debugging Authentication
~~~~~~~~~~~~~~~~~~~~~~~~

Enable debug logging to troubleshoot authentication issues:

.. code-block:: python

    import logging

    # Enable debug logging for authentication
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("athena_client.client.channel")
    logger.setLevel(logging.DEBUG)

    # Your authentication code here

Testing Authentication
~~~~~~~~~~~~~~~~~~~~~~

Test your authentication setup:

.. code-block:: python

    async def test_authentication():
        """Test OAuth authentication without full client setup."""
        try:
            credential_helper = CredentialHelper(
                client_id=os.getenv("OAUTH_CLIENT_ID"),
                client_secret=os.getenv("OAUTH_CLIENT_SECRET"),
            )

            token = credential_helper.get_token()
            print(f"✓ Authentication successful (token length: {len(token)})")
            return True

        except Exception as e:
            print(f"✗ Authentication failed: {e}")
            return False

    # Run the test
    success = await test_authentication()

Migration Guide
---------------

From Static Tokens to OAuth
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you're currently using static token authentication and want to migrate to OAuth:

1. **Obtain OAuth credentials** from your OAuth provider
2. **Update your environment variables**:

   .. code-block:: bash

       # Remove static token
       # ATHENA_TOKEN=your-static-token

       # Add OAuth credentials
       OAUTH_CLIENT_ID=your-client-id
       OAUTH_CLIENT_SECRET=your-client-secret

3. **Update your code**:

   .. code-block:: python

       # Old static token approach
       # channel = create_channel(host=host, auth_token=token)

       # New OAuth approach
       credential_helper = CredentialHelper(
           client_id=os.getenv("OAUTH_CLIENT_ID"),
           client_secret=os.getenv("OAUTH_CLIENT_SECRET"),
       )
       channel = await create_channel_with_credentials(host, credential_helper)

From Manual Token Management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you were manually managing OAuth tokens:

1. **Remove manual token logic**
2. **Use the credential helper** for automatic management
3. **Remove token refresh code** - it's handled automatically

Best Practices Summary
----------------------

1. **Use OAuth credential helper** for production applications
2. **Store credentials securely** using environment variables or secret management
3. **Never hardcode credentials** in source code
4. **Handle authentication errors** gracefully
5. **Monitor authentication** for security and operational issues
6. **Use different credentials** for development and production
7. **Test authentication** setup before deploying
8. **Enable debug logging** when troubleshooting

For more information, see:

* :doc:`examples` for complete authentication examples
* :doc:`api/client` for detailed API documentation
* :doc:`installation` for setup instructions
