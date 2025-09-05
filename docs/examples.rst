Examples
========

This section provides detailed examples of using the Athena Client library in various scenarios. All examples are available in the ``examples/`` directory of the repository.

Complete Examples
-----------------

OAuth Authentication Example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The main example demonstrates OAuth authentication with the credential helper. This is the recommended approach for production use.

**File**: ``examples/example.py``

This example shows:

* OAuth credential helper setup
* Automatic token acquisition and refresh
* Deployment selection
* Streaming image classification
* Error handling and logging
* Performance monitoring

**Basic Usage**:

.. code-block:: python

    import asyncio
    import os
    from dotenv import load_dotenv

    from athena_client.client.athena_client import AthenaClient
    from athena_client.client.athena_options import AthenaOptions
    from athena_client.client.channel import (
        CredentialHelper,
        create_channel_with_credentials,
    )
    from athena_client.client.deployment_selector import DeploymentSelector

    async def main():
        load_dotenv()

        # OAuth credentials from environment
        client_id = os.getenv("OAUTH_CLIENT_ID")
        client_secret = os.getenv("OAUTH_CLIENT_SECRET")
        auth_url = os.getenv(
            "OAUTH_AUTH_URL", "https://crispthinking.auth0.com/oauth/token"
        )
        audience = os.getenv("OAUTH_AUDIENCE", "crisp-athena-dev")
        host = os.getenv("ATHENA_HOST", "localhost")

        # Create credential helper
        credential_helper = CredentialHelper(
            client_id=client_id,
            client_secret=client_secret,
            auth_url=auth_url,
            audience=audience,
        )

        # Get available deployments
        channel = await create_channel_with_credentials(host, credential_helper)
        async with DeploymentSelector(channel) as deployment_selector:
            deployments = await deployment_selector.list_deployments()

        deployment_id = deployments.deployments[0].deployment_id

        # Configure client options
        options = AthenaOptions(
            host=host,
            resize_images=True,
            deployment_id=deployment_id,
            compress_images=True,
            timeout=120.0,
            keepalive_interval=30.0,
            affiliate="test-affiliate",
        )

        # Run classification
        async with AthenaClient(channel, options) as client:
            # Process images with streaming interface
            results = client.classify_images(iter_images())

            async for result in results:
                # Process classification results
                for output in result.outputs:
                    classifications = {
                        c.label: round(c.weight, 3)
                        for c in output.classifications
                    }
                    print(f"Result: {classifications}")

    asyncio.run(main())

Image Generation Utilities
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**File**: ``examples/create_image.py``

This utility module provides functions for generating test images:

.. code-block:: python

    from examples.create_image import iter_images, create_test_image

    # Generate test images for classification
    test_images = iter_images(max_images=10)

    # Create a single test image
    image_data = create_test_image(width=512, height=512)

Environment Configuration
-------------------------

All examples use environment variables for configuration. Create a ``.env`` file in the project root:

.. code-block:: bash

    # Required OAuth credentials
    OAUTH_CLIENT_ID=your-client-id
    OAUTH_CLIENT_SECRET=your-client-secret

    # Athena service configuration
    ATHENA_HOST=your-athena-host

    # Optional OAuth configuration (defaults shown)
    OAUTH_AUTH_URL=https://crispthinking.auth0.com/oauth/token
    OAUTH_AUDIENCE=crisp-athena-dev

Running the Examples
--------------------

1. **Install dependencies**:

   .. code-block:: bash

      uv sync --dev

2. **Set up environment variables** (create ``.env`` file as shown above)

3. **Run the OAuth example**:

   .. code-block:: bash

      cd examples
      python example.py

Static Token Authentication
---------------------------

For simpler use cases, you can use static token authentication:

.. code-block:: python

    from athena_client.client.channel import create_channel

    # Use a pre-existing authentication token
    channel = create_channel(host="your-host", auth_token="your-token")

    options = AthenaOptions(
        host="your-host",
        deployment_id="your-deployment-id",
        resize_images=True,
        compress_images=True,
        affiliate="your-affiliate",
    )

    async with AthenaClient(channel, options) as client:
        # Your classification logic here
        pass

Advanced Usage Patterns
------------------------

Error Handling
~~~~~~~~~~~~~~

The examples demonstrate comprehensive error handling:

.. code-block:: python

    from athena_client.client.utils import (
        get_output_error_summary,
        has_output_errors,
        process_classification_outputs,
    )

    async for result in results:
        # Check for output errors
        if has_output_errors(result):
            error_summary = get_output_error_summary(result)
            logger.warning("Received errors: %s", error_summary)

        # Process outputs with error handling
        successful_outputs = process_classification_outputs(
            result,
            raise_on_error=False,
            log_errors=True
        )

        for output in successful_outputs:
            # Process successful classifications
            pass

Performance Monitoring
~~~~~~~~~~~~~~~~~~~~~~

Track performance metrics in your applications:

.. code-block:: python

    import time

    sent_counter = [0]
    received_count = 0
    start_time = time.time()

    async for result in results:
        received_count += len(result.outputs)

        if received_count % 10 == 0:
            elapsed = time.time() - start_time
            rate = received_count / elapsed if elapsed > 0 else 0
            logger.info(
                "Sent %d requests, received %d responses (%.1f/sec)",
                sent_counter[0],
                received_count,
                rate,
            )

Batch Processing
~~~~~~~~~~~~~~~~

Process large numbers of images efficiently:

.. code-block:: python

    def iter_large_image_batch(image_paths):
        """Generator for processing large image batches."""
        for path in image_paths:
            with open(path, 'rb') as f:
                yield f.read()

    # Process with streaming interface
    results = client.classify_images(iter_large_image_batch(image_paths))

    async for batch_result in results:
        # Process results in batches
        for output in batch_result.outputs:
            # Handle individual classification
            pass

Configuration Options
---------------------

Key configuration options for different use cases:

Development/Testing
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    options = AthenaOptions(
        host="localhost:50051",
        resize_images=True,
        compress_images=False,  # Disable for faster testing
        timeout=60.0,
        affiliate="development",
    )

Production
~~~~~~~~~~

.. code-block:: python

    options = AthenaOptions(
        host="production-host:443",
        resize_images=True,
        compress_images=True,  # Enable for bandwidth efficiency
        timeout=300.0,
        keepalive_interval=60.0,
        affiliate="production-service",
    )

High Throughput
~~~~~~~~~~~~~~~

.. code-block:: python

    options = AthenaOptions(
        host="your-host",
        resize_images=True,
        compress_images=True,
        timeout=None,  # No timeout for long-running streams
        keepalive_interval=30.0,
        affiliate="high-throughput",
    )

Common Patterns
---------------

Async Context Managers
~~~~~~~~~~~~~~~~~~~~~~

Always use async context managers for proper resource cleanup:

.. code-block:: python

    async with AthenaClient(channel, options) as client:
        # Client is properly initialized
        results = client.classify_images(image_iterator)

        async for result in results:
            # Process results
            pass
    # Client is automatically cleaned up

Error Recovery
~~~~~~~~~~~~~~

Implement retry logic for robust applications:

.. code-block:: python

    import asyncio
    from athena_client.client.exceptions import AthenaClientError

    max_retries = 3
    retry_delay = 1.0

    for attempt in range(max_retries):
        try:
            async with AthenaClient(channel, options) as client:
                # Your classification logic
                break
        except AthenaClientError as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            await asyncio.sleep(retry_delay * (2 ** attempt))

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Authentication failures**:
   - Verify your OAuth credentials are correct
   - Check that the auth URL and audience match your configuration
   - Ensure your credentials have the necessary permissions

**Connection timeouts**:
   - Increase the timeout value in AthenaOptions
   - Check network connectivity to the Athena service
   - Verify the host and port are correct

**Image processing errors**:
   - Ensure images are in supported formats (JPEG, PNG)
   - Check image file sizes aren't too large
   - Verify image data is valid and not corrupted

**Memory issues with large batches**:
   - Process images in smaller batches
   - Use generators instead of loading all images into memory
   - Enable image compression to reduce memory usage

Getting Help
------------

For additional help:

* Review the full examples in the ``examples/`` directory
* Check the :doc:`api/index` documentation
* See the :doc:`installation` guide for setup issues
* Report bugs or request features on GitHub
