Athena Client
=============

A high-performance Python client library for interacting with Athena API
services for CSAM (Child Sexual Abuse Material) detection.

The Athena Client provides both synchronous and asynchronous interfaces for image classification, with built-in support for OAuth authentication, automatic token refresh, image preprocessing, and streaming responses.

Key Features
------------

* **Async/Await Interface**: High-performance asynchronous image classification
* **Connection Management**: Automatic reconnection and resource cleanup
* **Error Handling**: Comprehensive error types and recovery strategies
* **Image Processing Pipeline**: Built-in resizing, compression, and optimization
* **OAuth Authentication**: Automatic token acquisition and refresh with credential helper
* **Streaming Responses**: Process large batches efficiently with async iterators
* **Type Safety**: Full type hints throughout the codebase

Quick Start
-----------

.. code-block:: python

    import asyncio
    from athena_client.client.channel import CredentialHelper, create_channel_with_credentials
    from athena_client.client.athena_client import AthenaClient
    from athena_client.client.athena_options import AthenaOptions

    async def main():
        credential_helper = CredentialHelper(
            client_id="your-client-id",
            client_secret="your-client-secret",
            auth_url="https://crispthinking.auth0.com/oauth/token",
            audience="crisp-athena"
        )

        channel = await create_channel_with_credentials(
            host="your-athena-host",
            credential_helper=credential_helper
        )

        options = AthenaOptions(
            host="your-athena-host",
            deployment_id="your-deployment-id",
            affiliate="your-affiliate"
        )

        async with AthenaClient(channel, options) as client:
            # Your classification logic here
            pass

    asyncio.run(main())

Documentation
-------------

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   installation
   examples
   authentication

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/index

.. toctree::
   :maxdepth: 2
   :caption: Development

   development
   contributing

Authentication Methods
----------------------

The Athena Client supports two authentication approaches:

OAuth Credential Helper (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The credential helper automatically handles OAuth token acquisition and refresh:

* Automatic token refresh when tokens expire
* Thread-safe token caching for concurrent requests
* Comprehensive error handling for OAuth failures
* Configurable OAuth endpoints and audiences

Development
-----------

This project uses modern Python development tools:

* **uv** for fast dependency management
* **pytest** for comprehensive testing
* **ruff** for linting and formatting
* **pyright** for type checking
* **pre-commit** hooks for code quality

See the :doc:`development` guide for detailed setup instructions.

Support
-------

* Review the :doc:`examples` for common usage patterns
* Check the :doc:`api/index` for detailed API documentation
* See :doc:`athena_protobufs:index` for gRPC API documentation.
* Report issues on GitHub
* Follow development guidelines in :doc:`contributing`

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
