Transformers Reference
====================

The Athena Client includes several transformers for processing image data and requests.
Each transformer implements the :class:`AsyncTransformer` base class and provides
specific functionality in the image processing pipeline.

Image Processing
--------------

.. currentmodule:: athena_client.client.transformers

ClassificationInputTransformer
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: ClassificationInputTransformer
   :members:
   :undoc-members:
   :special-members: __init__
   :show-inheritance:

Transforms raw image bytes into properly formatted classification input objects.

ImageResizer
~~~~~~~~~~

.. autoclass:: ImageResizer
   :members:
   :undoc-members:
   :special-members: __init__
   :show-inheritance:

Resizes images to meet model input requirements while maintaining aspect ratio.

Compression
---------

BrotliCompressor
~~~~~~~~~~~~~

.. autoclass:: BrotliCompressor
   :members:
   :undoc-members:
   :special-members: __init__
   :show-inheritance:

Compresses image data using the Brotli algorithm to reduce bandwidth usage.

Request Handling
-------------

RequestBatcher
~~~~~~~~~~~

.. autoclass:: RequestBatcher
   :members:
   :undoc-members:
   :special-members: __init__
   :show-inheritance:

Batches individual requests together for more efficient processing.

Base Classes
----------

AsyncTransformer
~~~~~~~~~~~~~

.. autoclass:: athena_client.client.transformers.async_transformer.AsyncTransformer
   :members:
   :undoc-members:
   :special-members: __init__
   :show-inheritance:

Base class that all transformers inherit from, implementing the async iteration protocol.
