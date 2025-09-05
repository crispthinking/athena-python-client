Configuration Options
=====================

.. currentmodule:: athena_client.client.athena_options

The options module provides configuration classes for customizing client behavior, connection settings, and processing options.

AthenaOptions
-------------

.. autoclass:: AthenaOptions
   :members:
   :undoc-members:
   :special-members: __init__
   :show-inheritance:
   :no-index:

   Main configuration class for the Athena client. Controls connection settings,
   processing options, and performance tuning.

   Example:
       >>> options = AthenaOptions(
       ...     host="athena.example.com",
       ...     deployment_id="prod-deployment",
       ...     resize_images=True,
       ...     compress_images=True,
       ...     timeout=120.0,
       ...     affiliate="my-service"
       ... )

Configuration Parameters
------------------------

Connection Settings
~~~~~~~~~~~~~~~~~~~

**host** : str
    The hostname or address of the Athena service.

    Example: ``"athena.example.com"`` or ``"localhost:50051"``

**deployment_id** : str
    The deployment identifier for the specific model version to use.

    Example: ``"prod-v1.2"`` or ``"dev-latest"``

**timeout** : float, optional
    Maximum time in seconds to wait for responses. Set to ``None`` for no timeout.

    Default: ``120.0``

**keepalive_interval** : float, optional
    Interval in seconds for sending keepalive messages to maintain connection.

    Default: ``30.0``

**max_message_size** : int, optional
    Maximum size in bytes for gRPC messages.

    Default: ``100 * 1024 * 1024`` (100MB)

Processing Options
~~~~~~~~~~~~~~~~~~

**resize_images** : bool, optional
    Whether to automatically resize images for optimal processing.

    Default: ``True``

**compress_images** : bool, optional
    Whether to compress image data using Brotli compression.

    Default: ``True``

**affiliate** : str, optional
    Affiliate identifier for tracking and billing purposes.

    Example: ``"my-organization"``

Configuration Examples
----------------------

Development Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from athena_client.client.athena_options import AthenaOptions

    # Development setup
    dev_options = AthenaOptions(
        host="localhost:50051",
        deployment_id="dev-latest",
        resize_images=True,
        compress_images=False,  # Disable for faster local testing
        timeout=60.0,
        affiliate="development"
    )

Production Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Production setup
    prod_options = AthenaOptions(
        host="athena.prod.example.com",
        deployment_id="prod-v1.2",
        resize_images=True,
        compress_images=True,  # Enable for bandwidth efficiency
        timeout=300.0,  # Longer timeout for production loads
        keepalive_interval=60.0,
        max_message_size=200 * 1024 * 1024,  # 200MB for large images
        affiliate="production-service"
    )

High-Throughput Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # High-throughput setup
    high_throughput_options = AthenaOptions(
        host="athena.cluster.example.com",
        deployment_id="high-perf-v2.0",
        resize_images=True,
        compress_images=True,
        timeout=None,  # No timeout for long-running streams
        keepalive_interval=30.0,
        max_message_size=500 * 1024 * 1024,  # 500MB for batch processing
        affiliate="batch-processor"
    )

Low-Latency Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Low-latency setup
    low_latency_options = AthenaOptions(
        host="athena.edge.example.com",
        deployment_id="fast-inference",
        resize_images=False,  # Skip resizing for speed
        compress_images=False,  # Skip compression for speed
        timeout=10.0,  # Short timeout for real-time use
        keepalive_interval=5.0,  # Frequent keepalives
        affiliate="real-time-service"
    )

Environment-Based Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import os
    from athena_client.client.athena_options import AthenaOptions

    # Load from environment variables
    options = AthenaOptions(
        host=os.getenv("ATHENA_HOST", "localhost:50051"),
        deployment_id=os.getenv("ATHENA_DEPLOYMENT_ID", "default"),
        resize_images=os.getenv("ATHENA_RESIZE_IMAGES", "true").lower() == "true",
        compress_images=os.getenv("ATHENA_COMPRESS_IMAGES", "true").lower() == "true",
        timeout=float(os.getenv("ATHENA_TIMEOUT", "120.0")),
        affiliate=os.getenv("ATHENA_AFFILIATE", "default")
    )

Performance Tuning
-------------------

Image Processing
~~~~~~~~~~~~~~~~

**resize_images=True**:
    - Automatically optimizes image dimensions for the model
    - Reduces processing time and bandwidth
    - Recommended for most use cases

**resize_images=False**:
    - Uses original image dimensions
    - Faster if images are already optimized
    - May increase bandwidth usage

**compress_images=True**:
    - Uses Brotli compression to reduce bandwidth
    - Slight CPU overhead for compression/decompression
    - Recommended for network-constrained environments

**compress_images=False**:
    - No compression overhead
    - Higher bandwidth usage
    - Recommended for local or high-bandwidth connections

Connection Tuning
~~~~~~~~~~~~~~~~~

**timeout**:
    - Set based on expected response times
    - Use ``None`` for long-running streams
    - Balance between responsiveness and reliability

**keepalive_interval**:
    - Shorter intervals for unreliable networks
    - Longer intervals for stable connections
    - Affects resource usage on both client and server

**max_message_size**:
    - Increase for large images or batch processing
    - Balance with memory usage
    - Consider network MTU and buffering

Best Practices
--------------

Environment-Specific Settings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def create_options_for_environment(env: str) -> AthenaOptions:
        """Create options appropriate for the deployment environment."""
        base_config = {
            "resize_images": True,
            "affiliate": f"service-{env}"
        }

        if env == "development":
            return AthenaOptions(
                host="localhost:50051",
                deployment_id="dev-latest",
                compress_images=False,
                timeout=60.0,
                **base_config
            )
        elif env == "staging":
            return AthenaOptions(
                host="athena.staging.example.com",
                deployment_id="staging-v1.0",
                compress_images=True,
                timeout=120.0,
                **base_config
            )
        elif env == "production":
            return AthenaOptions(
                host="athena.prod.example.com",
                deployment_id="prod-v1.2",
                compress_images=True,
                timeout=300.0,
                keepalive_interval=60.0,
                **base_config
            )
        else:
            raise ValueError(f"Unknown environment: {env}")

Configuration Validation
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def validate_options(options: AthenaOptions) -> None:
        """Validate configuration options."""
        if not options.host:
            raise ValueError("Host must be specified")

        if not options.deployment_id:
            raise ValueError("Deployment ID must be specified")

        if options.timeout is not None and options.timeout <= 0:
            raise ValueError("Timeout must be positive or None")

        if options.keepalive_interval <= 0:
            raise ValueError("Keepalive interval must be positive")

        if options.max_message_size <= 0:
            raise ValueError("Max message size must be positive")

Configuration from Files
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import json
    from pathlib import Path
    from athena_client.client.athena_options import AthenaOptions

    def load_options_from_file(config_path: Path) -> AthenaOptions:
        """Load configuration from a JSON file."""
        with open(config_path) as f:
            config = json.load(f)

        return AthenaOptions(**config)

    # Example config.json:
    # {
    #   "host": "athena.example.com",
    #   "deployment_id": "prod-v1.2",
    #   "resize_images": true,
    #   "compress_images": true,
    #   "timeout": 120.0,
    #   "affiliate": "my-service"
    # }

Migration Guide
---------------

From Version 0.1.x
~~~~~~~~~~~~~~~~~~~

If upgrading from earlier versions:

.. code-block:: python

    # Old approach (deprecated)
    # client = AthenaClient(host="...", deployment_id="...")

    # New approach
    options = AthenaOptions(
        host="your-host",
        deployment_id="your-deployment-id"
    )
    client = AthenaClient(channel, options)

Common Issues
-------------

Invalid Host Format
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Incorrect - missing port for non-standard ports
    # options = AthenaOptions(host="athena.example.com")

    # Correct - include port if non-standard
    options = AthenaOptions(host="athena.example.com:443")

Timeout Configuration
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # For long-running operations
    options = AthenaOptions(
        host="your-host",
        deployment_id="your-deployment",
        timeout=None  # No timeout
    )

    # For real-time applications
    options = AthenaOptions(
        host="your-host",
        deployment_id="your-deployment",
        timeout=5.0  # 5 second timeout
    )

Memory Usage
~~~~~~~~~~~~

.. code-block:: python

    # For memory-constrained environments
    options = AthenaOptions(
        host="your-host",
        deployment_id="your-deployment",
        max_message_size=10 * 1024 * 1024,  # 10MB limit
        compress_images=True  # Reduce bandwidth
    )

See Also
--------

* :doc:`client` - Client interface using these options
* :doc:`../examples` - Complete usage examples
* :doc:`../authentication` - Authentication configuration
