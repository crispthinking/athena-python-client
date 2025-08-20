Athena Client
============

A high-performance Python client for interacting with Athena services.

Features:

* **Async/await interface** - Built for modern Python applications
* **Image classification** - Process images with state-of-the-art models
* **Batch processing** - Efficient handling of multiple images
* **Automatic optimization** - Image resizing and compression
* **Strong typing** - Full type hint coverage for better IDE support

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   quickstart
   installation
   examples

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/client
   api/transformers
   api/options
   api/exceptions
   api/grpc_wrappers
   api/deployment_selector
   api/correlation

.. toctree::
   :maxdepth: 2
   :caption: Development

   contributing

Quick Example
-----------

.. code-block:: python

   from athena_client import AthenaClient, AthenaOptions

   async def process_images(image_paths):
       # Configure the client
       options = AthenaOptions(
           host="api.example.com",
           resize_images=True,
           compress_images=True
       )

       # Use context manager for automatic cleanup
       async with AthenaClient(options=options) as client:
           for path in image_paths:
               with open(path, "rb") as f:
                   image_data = f.read()

               # Process each image
               async for result in client.classify_images([image_data]):
                   print(f"Classification for {path}: {result}")

Project Links
-----------

* `Issue Tracker <https://github.com/your-org/athena-client/issues>`_
* `Source Code <https://github.com/your-org/athena-client>`_
