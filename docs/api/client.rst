Client Interface
================

.. currentmodule:: resolver_athena_client.client

The client module provides the main interface for interacting with Athena
services, including the primary client class and authentication helpers.

AthenaClient
------------

The main client class for image classification. Provides an async context manager
interface for proper resource management and cleanup.

Example:
    >>> async with AthenaClient(channel, options) as client:
    ...     results = client.classify_images(image_iterator)
    ...     async for result in results:
    ...         print(result.outputs)


.. currentmodule:: resolver_athena_client.client.athena_client

.. autoclass:: AthenaClient
   :members:
   :undoc-members:
   :special-members: __init__
   :show-inheritance:

Channel Management
------------------

.. currentmodule:: resolver_athena_client.client.channel

.. autofunction:: create_channel_with_credentials

.. autoclass:: CredentialHelper
   :members:
   :undoc-members:
   :special-members: __init__
   :show-inheritance:

   OAuth credential helper for automatic token management and refresh.

   Example:
       >>> credential_helper = CredentialHelper(
       ...     client_id="your-client-id",
       ...     client_secret="your-client-secret"
       ... )
       >>> channel = await create_channel_with_credentials(
       ...     host="your-host",
       ...     credential_helper=credential_helper
       ... )

Deployment Selection
--------------------

.. currentmodule:: resolver_athena_client.client.deployment_selector

See :doc:`deployment_selector` for deployment discovery and selection functionality.

Correlation and Tracing
-----------------------

.. currentmodule:: resolver_athena_client.client.correlation

.. autoclass:: CorrelationProvider
   :members:
   :undoc-members:
   :special-members: __init__
   :show-inheritance:
   :no-index:

.. autoclass:: HashCorrelationProvider
   :members:
   :undoc-members:
   :special-members: __init__
   :show-inheritance:
   :no-index:

   Hash-based correlation ID provider for deterministic correlation IDs.

   Example:
       >>> provider = HashCorrelationProvider()
       >>> correlation_id = provider.get_correlation_id(image_data)

Utility Functions
-----------------

.. currentmodule:: resolver_athena_client.client.utils

.. autofunction:: process_classification_outputs

.. autofunction:: has_output_errors

.. autofunction:: get_output_error_summary

   Utility functions for processing classification results and handling errors.

   Example:
       >>> if has_output_errors(result):
       ...     error_summary = get_output_error_summary(result)
       ...     logger.warning(f"Errors: {error_summary}")
       >>>
       >>> successful_outputs = process_classification_outputs(
       ...     result, raise_on_error=False, log_errors=True
       ... )

Constants
---------

.. currentmodule:: resolver_athena_client.client.consts

Common constants used throughout the client library.

.. autodata:: EXPECTED_WIDTH
.. autodata:: EXPECTED_HEIGHT

   Expected image dimensions for optimal classification performance.

Usage Examples
--------------

Basic Classification
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import asyncio
    from resolver_athena_client.client.athena_client import AthenaClient
    from resolver_athena_client.client.athena_options import AthenaOptions
    from resolver_athena_client.client.channel import create_channel

    async def main():
        # Create channel with static token
        channel = create_channel(
            host="your-host",
            auth_token="your-token"
        )

        # Configure client options (see api/options for details)
        options = AthenaOptions(
            host="your-host",
            deployment_id="your-deployment-id",
            resize_images=True,
            compress_images=True
        )

        # Use client for classification
        async with AthenaClient(channel, options) as client:
            results = client.classify_images(image_iterator)

            async for result in results:
                for output in result.outputs:
                    # Manually map classifications, as the generated grpc
                    # implementation for __str__ will ignore weights of 0.0,
                    # which are common, especially for binary classifications
                    # such as hash checks
                    classifications = {
                        c.label: c.weight
                        for c in output.classifications
                    }
                    print(f"Classifications: {classifications}")

    asyncio.run(main())

OAuth Authentication
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import asyncio
    import os
    from resolver_athena_client.client.athena_client import AthenaClient
    from resolver_athena_client.client.athena_options import AthenaOptions
    from resolver_athena_client.client.channel import (
        CredentialHelper,
        create_channel_with_credentials
    )

    async def main():
        # Create OAuth credential helper
        credential_helper = CredentialHelper(
            client_id=os.getenv("OAUTH_CLIENT_ID"),
            client_secret=os.getenv("OAUTH_CLIENT_SECRET")
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
            compress_images=True
        )

        async with AthenaClient(channel, options) as client:
            # Your classification logic here
            pass

    asyncio.run(main())

Error Handling
~~~~~~~~~~~~~~

.. code-block:: python

    from resolver_athena_client.client.exceptions import (
        AthenaClientError,
        AuthenticationError,
        ConnectionError
    )
    from resolver_athena_client.client.utils import (
        process_classification_outputs,
        has_output_errors
    )

    try:
        async with AthenaClient(channel, options) as client:
            results = client.classify_images(image_iterator)

            async for result in results:
                # Check for errors in the result
                if has_output_errors(result):
                    logger.warning("Some outputs had errors")

                # Process successful outputs
                successful_outputs = process_classification_outputs(
                    result,
                    raise_on_error=False,
                    log_errors=True
                )

                for output in successful_outputs:
                    # Handle successful classification
                    pass

    except AuthenticationError as e:
        logger.error(f"Authentication failed: {e}")
    except ConnectionError as e:
        logger.error(f"Connection failed: {e}")
    except AthenaClientError as e:
        logger.error(f"Client error: {e}")

Performance Optimization
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Configure for high throughput (see api/options for all options)
    options = AthenaOptions(
        host="your-host",
        deployment_id="your-deployment-id",
        resize_images=True,
        compress_images=True,
        timeout=300.0,  # 5 minute timeout
        keepalive_interval=60.0,  # 1 minute keepalive
    )

    async with AthenaClient(channel, options) as client:
        # Use streaming for large batches
        results = client.classify_images(large_image_iterator)

        async for batch_result in results:
            # Process in batches for better performance
            await process_batch(batch_result.outputs)

Notes
-----

* Always use the client as an async context manager to ensure proper cleanup
* The client handles connection management and retries automatically
* Use correlation IDs for request tracing in distributed systems
* Enable compression for bandwidth-constrained environments
* Configure appropriate timeouts for your use case
* See :doc:`options` for detailed configuration options
* Carefully handle any logging of classification results, as decribed in the
  basic classification example above, to avoid losing important information
