Examples
========

This section provides detailed examples of using the Athena Client library in various scenarios.

Usage Examples
------------------

Simple Client Setup
~~~~~~~~~~~~~~~~~

.. code-block:: python

    from athena_client import AthenaClient

    async def main():
        host = os.environ.get("ATHENA_HOST")
        client_id = os.environ.get("ATHENA_CLIENT_ID")
        client_secret = os.environ.get("ATHENA_CLIENT_SECRET")
        auth_url = os.environ.get("ATHENA_AUTH_URL")
        audience = os.environ.get("ATHENA_AUDIENCE")

        credential_helper = CredentialHelper(
            client_id=client_id,
            client_secret=client_secret,
            auth_url=auth_url,
            audience=audience,
        )

        channel = await create_channel_with_credentials(host, credential_helper)

        options = AthenaOptions(
            host=host,
            deployment_id=deployment_id,
            resize_images=True,
            compress_images=True,
            affiliate="crisp",
        )

        async with AthenaClient(channel, options) as client:
            # Your code here
            pass
