API Reference
=============

Overview
--------

The Athena Client library provides a comprehensive set of components for interacting with Athena services. The API is designed around async/await patterns and provides both high-level convenience interfaces and low-level control when needed.

Main Components
---------------

Client Interface
~~~~~~~~~~~~~~~~

The :doc:`client` module provides the primary interface for image classification:

* **AthenaClient**: Main client class with async context manager support
* **AthenaOptions**: Configuration and options for client behavior
* **Channel management**: Connection handling and authentication

Key Features:
* Async/await interface for high-performance operations
* Automatic connection management and cleanup
* Built-in retry logic and error recovery
* Streaming interface for batch processing

Authentication
~~~~~~~~~~~~~~

Authentication is handled through the channel module:

* **OAuth credential helper**: Automatic token management and refresh
* **Static token support**: Direct token authentication
* **Secure credential handling**: Environment variable integration

Processing Pipeline
~~~~~~~~~~~~~~~~~~~~

The :doc:`transformers` module provides image processing capabilities:

* **Image resizing**: Automatic optimization for classification
* **Compression**: Brotli compression for bandwidth efficiency
* **Format conversion**: Support for multiple image formats
* **Validation**: Image data validation and error handling

Error Management
~~~~~~~~~~~~~~~~

The :doc:`exceptions` module defines structured error types:

* **Hierarchical exceptions**: Clear error categorization
* **Detailed error context**: Rich error information
* **Recovery strategies**: Guidelines for error handling

Core Modules
------------

.. toctree::
   :maxdepth: 2

   client
   options
   exceptions
   grpc_wrappers
   deployment_selector
   correlation

Module Details
--------------

athena_client.client
~~~~~~~~~~~~~~~~~~~~

The main client module containing:

* ``AthenaClient``: Primary client interface
* ``AthenaOptions``: Configuration class
* ``CredentialHelper``: OAuth authentication helper
* ``create_channel``: Channel creation utilities

athena_client.client.transformers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Image processing pipeline components:

* ``ImageResizer``: Resize images for optimal processing
* ``BrotliCompressor``: Compress image data
* ``ImageValidator``: Validate image formats and data
* ``Pipeline``: Combine multiple transformers

athena_client.client.exceptions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Exception hierarchy for error handling:

* ``AthenaClientError``: Base exception class
* ``AuthenticationError``: Authentication failures
* ``ConnectionError``: Network and connection issues
* ``ValidationError``: Input validation failures
* ``ProcessingError``: Image processing errors

athena_client.grpc_wrappers
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Low-level gRPC integration:

* Service-specific wrappers
* Protocol buffer integration
* Connection management
* Error translation from gRPC to client exceptions

Usage Patterns
--------------

Basic Client Usage
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from athena_client.client.athena_client import AthenaClient
    from athena_client.client.athena_options import AthenaOptions
    from athena_client.client.channel import create_channel_with_credentials

    # Setup
    options = AthenaOptions(
        host="your-host",
        deployment_id="deployment-id",
        resize_images=True,
        compress_images=True
    )

    # Usage
    async with AthenaClient(channel, options) as client:
        results = client.classify_images(image_iterator)
        async for result in results:
            # Process results
            pass

Error Handling
~~~~~~~~~~~~~~

.. code-block:: python

    from athena_client.client.exceptions import (
        AthenaClientError,
        AuthenticationError,
        ConnectionError
    )

    try:
        async with AthenaClient(channel, options) as client:
            # Your code here
            pass
    except AuthenticationError:
        # Handle auth failures
        pass
    except ConnectionError:
        # Handle connection issues
        pass
    except AthenaClientError:
        # Handle other client errors
        pass

Pipeline Processing
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from athena_client.client.transformers import ImageResizer, BrotliCompressor

    # Create processing pipeline
    resizer = ImageResizer(target_size=(512, 512))
    compressor = BrotliCompressor()

    # Process images
    async for image_data in image_iterator:
        resized = await resizer.transform(image_data)
        compressed = await compressor.transform(resized)
        # Send for classification

Type Information
----------------

The library provides comprehensive type hints for all public APIs. Key types include:

* ``AsyncIterator[bytes]``: Image data streams
* ``ClassificationResult``: Classification output
* ``ProcessedImage``: Processed image data
* ``DeploymentInfo``: Service deployment information

For complete type information, see the individual module documentation.

Configuration
-------------

Client behavior is controlled through :doc:`options`:

* **Connection settings**: Host, timeouts, keepalive
* **Processing options**: Image resizing, compression
* **Authentication**: Credential configuration
* **Performance tuning**: Batch sizes, concurrency

See the :doc:`options` documentation for complete configuration details.

Integration Examples
--------------------

For practical usage examples, see:

* :doc:`../examples` - Complete usage examples
* :doc:`../authentication` - Authentication setup
* :doc:`../installation` - Development setup

The examples show real-world usage patterns and best practices for different scenarios.

Advanced Usage
--------------

Custom Transformers
~~~~~~~~~~~~~~~~~~~

Extend the processing pipeline with custom transformers:

.. code-block:: python

    from athena_client.client.transformers.base import BaseTransformer

    class CustomTransformer(BaseTransformer):
        async def transform(self, data: bytes) -> bytes:
            # Custom processing logic
            return processed_data

Deployment Selection
~~~~~~~~~~~~~~~~~~~~

Dynamically select deployments:

.. code-block:: python

    from athena_client.client.deployment_selector import DeploymentSelector

    async with DeploymentSelector(channel) as selector:
        deployments = await selector.list_deployments()
        # Choose appropriate deployment

Request Correlation
~~~~~~~~~~~~~~~~~~~

Track requests across the system:

.. code-block:: python

    from athena_client.client.correlation import generate_correlation_id

    correlation_id = generate_correlation_id()
    # Use correlation_id for request tracing

Performance Considerations
--------------------------

For optimal performance:

* **Use async context managers**: Ensures proper resource cleanup
* **Stream large batches**: Process images in streams rather than loading all into memory
* **Enable compression**: Reduces bandwidth usage
* **Configure timeouts**: Set appropriate timeouts for your use case
* **Monitor correlations**: Use correlation IDs for request tracking

See the performance section in :doc:`../examples` for detailed guidance.
