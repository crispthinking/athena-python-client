Correlation System
==================

The correlation system provides mechanisms for generating and managing
correlation IDs for requests. This system enables request tracing,
deduplication, and logging correlation across the service.

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

    options = AthenaOptions(
        correlation_provider=HashCorrelationProvider
    )

    async with AthenaClient(channel, options) as client:
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

Security Considerations
---------------------

When implementing correlation systems:

- Avoid including sensitive data in correlation IDs
- Be mindful of correlation ID length and format
- Make sure each image has a unique correlation ID
