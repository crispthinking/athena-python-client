Quickstart Guide
===============

This guide will get you up and running with the Athena Client library quickly.

Basic Usage
----------

Here's a simple example of how to use the Athena Client:

.. code-block:: python

    from athena_client import AthenaClient

    async def main():
        # Initialize the client
        client = AthenaClient()

        try:
            # Your Athena operations here
            response = await client.some_operation()

        finally:
            # Always close the client when done
            await client.close()

Common Operations
---------------

Here are some common operations you might want to perform:

Authentication
~~~~~~~~~~~~~

.. code-block:: python

    from athena_client import AthenaClient

    client = AthenaClient(
        api_key="your_api_key_here",
        base_url="https://api.athena.example.com"
    )

Error Handling
~~~~~~~~~~~~

The client includes robust error handling:

.. code-block:: python

    from athena_client import AthenaClient, AthenaError

    async def example():
        client = AthenaClient()
        try:
            response = await client.some_operation()
        except AthenaError as e:
            print(f"An error occurred: {e}")
        finally:
            await client.close()

Async Usage
----------

The Athena Client is built with async/await support:

.. code-block:: python

    import asyncio
    from athena_client import AthenaClient

    async def process_items(items):
        async with AthenaClient() as client:
            tasks = [client.process_item(item) for item in items]
            results = await asyncio.gather(*tasks)
            return results

    # Run the async function
    items = ["item1", "item2", "item3"]
    results = asyncio.run(process_items(items))

Configuration Options
------------------

The client can be configured with various options:

.. code-block:: python

    client = AthenaClient(
        api_key="your_api_key",
        base_url="https://api.example.com",
        timeout=30,
        max_retries=3,
        retry_delay=1.0
    )

Next Steps
---------

Now that you're familiar with the basics, you can:

* Review the :doc:`api/index` for detailed API documentation
* Check out the examples section for more complex usage patterns
* Read about advanced features in the specific API sections
* Learn about error handling in the API documentation

Need Help?
---------

If you run into issues:

* Check the installation guide above for setup problems
* Review the API documentation for correct usage
* File an issue on GitHub if you think you've found a bug
* Contact the maintainers for additional support
