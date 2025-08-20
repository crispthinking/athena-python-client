Examples
========

This section provides detailed examples of using the Athena Client library in various scenarios.

Basic Usage Examples
------------------

Simple Client Setup
~~~~~~~~~~~~~~~~~

.. code-block:: python

    from athena_client import AthenaClient

    async def main():
        async with AthenaClient() as client:
            # Your code here
            pass

Error Handling
~~~~~~~~~~~~

.. code-block:: python

    from athena_client import AthenaClient, AthenaError

    async def handle_errors():
        client = AthenaClient()
        try:
            # Your operations here
            pass
        except AthenaError as e:
            print(f"An error occurred: {e}")
        finally:
            await client.close()

Advanced Usage Examples
--------------------

Parallel Processing
~~~~~~~~~~~~~~~~~

.. code-block:: python

    import asyncio
    from athena_client import AthenaClient

    async def process_multiple_items(items):
        async with AthenaClient() as client:
            tasks = [client.process_item(item) for item in items]
            results = await asyncio.gather(*tasks)
            return results

Custom Configuration
~~~~~~~~~~~~~~~~~

.. code-block:: python

    from athena_client import AthenaClient

    async def custom_setup():
        client = AthenaClient(
            timeout=30,
            max_retries=3,
            retry_delay=1.0
        )
        try:
            # Your code here
            pass
        finally:
            await client.close()

Real-World Scenarios
-----------------

These examples demonstrate common real-world use cases for the Athena Client.

Batch Processing
~~~~~~~~~~~~~~

.. code-block:: python

    from athena_client import AthenaClient
    from typing import List

    async def batch_process(items: List[str], batch_size: int = 10):
        async with AthenaClient() as client:
            batches = [items[i:i + batch_size]
                      for i in range(0, len(items), batch_size)]

            results = []
            for batch in batches:
                batch_results = await asyncio.gather(
                    *[client.process_item(item) for item in batch]
                )
                results.extend(batch_results)

            return results

Error Retry Pattern
~~~~~~~~~~~~~~~~

.. code-block:: python

    import asyncio
    from athena_client import AthenaClient, AthenaError

    async def retry_operation(max_retries: int = 3, delay: float = 1.0):
        client = AthenaClient()

        for attempt in range(max_retries):
            try:
                result = await client.some_operation()
                return result
            except AthenaError as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(delay * (attempt + 1))

        await client.close()

Best Practices
------------

When using the Athena Client, keep these best practices in mind:

1. Always use async context managers (``async with``) when possible
2. Implement proper error handling
3. Close clients when done
4. Use batching for large operations
5. Configure appropriate timeouts
6. Implement retry logic for unreliable operations

For more detailed API documentation, see the :doc:`api/index` section.
