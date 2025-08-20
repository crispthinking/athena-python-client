Correlation System
==================

The correlation system provides mechanisms for generating and managing correlation IDs for requests. This system enables request tracing, deduplication, and logging correlation across the service.

.. module:: athena_client.client.correlation

Correlation Providers
-------------------

.. autoclass:: CorrelationProvider
   :members:
   :special-members: __init__
   :show-inheritance:

.. autoclass:: HashCorrelationProvider
   :members:
   :special-members: __init__
   :show-inheritance:

Usage
----------------

The correlation system is used internally by the client but can also be used directly::

    # Create a correlation provider
    provider = HashCorrelationProvider()

    # Generate a correlation ID for some input
    correlation_id = provider.get_correlation_id("my-input-data")

    # Use with client operations
    async with AthenaClient(..., correlation_provider=provider) as client:
        # The client will automatically generate correlation IDs
        results = await client.classify_images(...)

Best Practices
-------------

- Use a consistent correlation provider across related operations
- Consider data privacy when selecting correlation strategies
- Log correlation IDs for debugging and tracing
- Implement custom providers for specific needs

Custom Providers
--------------

You can implement custom correlation providers by subclassing CorrelationProvider::

    class TimestampCorrelationProvider(CorrelationProvider):
        def get_correlation_id(self, input_data: bytes | str | bytearray) -> str:
            # Generate timestamp-based correlation ID
            return f"{time.time_ns()}-{hash(input_data)}"

Error Handling
-------------

Correlation providers may raise the following exceptions:

- ``ValueError``: For invalid input data or conversion errors
- ``NotImplementedError``: When using abstract base class methods directly

Security Considerations
---------------------

When implementing correlation systems:

- Avoid including sensitive data in correlation IDs
- Use cryptographically secure hashing when needed
- Consider the uniqueness requirements of your use case
- Be mindful of correlation ID length and format
