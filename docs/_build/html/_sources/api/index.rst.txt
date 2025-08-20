API Reference
============

Overview
--------

The Athena Client library provides several key components:

Client
~~~~~~
The :doc:`client` provides the main interface for interacting with Athena services. It includes:

* Async/await interface for image classification
* Automatic connection and resource management
* Built-in error handling and retries

Transformers
~~~~~~~~~~~
The :doc:`transformers` module contains pipeline components for image processing:

* Image resizing and optimization
* Brotli compression
* Request batching
* Classification input preparation

Configuration
~~~~~~~~~~~
All client configuration is handled through :doc:`options`, which includes:

* Connection settings
* Processing options
* Performance tuning
* Authentication

Error Handling
~~~~~~~~~~~~
The :doc:`exceptions` module provides structured error types:

* Clear error hierarchies
* Specific error types for common issues
* Detailed error messages and context

GRPC Integration
~~~~~~~~~~~~~~
The :doc:`grpc_wrappers` module provides low-level GRPC components:

* Channel management and connection handling
* Service-specific wrappers
* Protocol buffer integration

Utilities
~~~~~~~~~~~~~~
Core utilities that support the main functionality:

* :doc:`deployment_selector` - Deployment discovery and selection
* :doc:`correlation` - Request correlation and tracing
* Built-in retry and backoff strategies
