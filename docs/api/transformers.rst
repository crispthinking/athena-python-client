Image Transformers
==================

The transformers module provides a pipeline of image processing components that prepare images for classification. These transformers work asynchronously and can be chained together to create custom processing pipelines.

Overview
--------

Transformers are designed around the async/await pattern and implement a common interface for processing image data. They can be used individually or combined into processing pipelines.

Base Classes
------------

.. automodule:: resolver_athena_client.client.transformers.async_transformer
   :members:
   :undoc-members:
   :show-inheritance:

Core Transformers
-----------------

Image Resizer
~~~~~~~~~~~~~

.. automodule:: resolver_athena_client.client.transformers.image_resizer
   :members:
   :undoc-members:
   :show-inheritance:

The ``ImageResizer`` automatically resizes images to optimal dimensions for classification while maintaining aspect ratio and image quality.

**Key Features:**

* Automatic aspect ratio preservation
* Multiple resampling algorithms
* Configurable target dimensions
* Format preservation

**Example Usage:**

.. code-block:: python

    from resolver_athena_client.client.transformers import ImageResizer

    resizer = ImageResizer(target_size=(512, 512))
    resized_data = await resizer.transform(image_data)

Brotli Compressor
~~~~~~~~~~~~~~~~~

.. automodule:: resolver_athena_client.client.transformers.brotli_compressor
   :members:
   :undoc-members:
   :show-inheritance:

The ``BrotliCompressor`` provides efficient compression of image data to reduce bandwidth usage during transmission.

**Key Features:**

* High compression ratios
* Fast compression/decompression
* Configurable compression levels
* Automatic format detection

**Example Usage:**

.. code-block:: python

    from resolver_athena_client.client.transformers import BrotliCompressor

    compressor = BrotliCompressor(quality=6)
    compressed_data = await compressor.transform(image_data)

Classification Input Transformer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: resolver_athena_client.client.transformers.classification_input
   :members:
   :undoc-members:
   :show-inheritance:

The ``ClassificationInputTransformer`` converts processed image data into the protobuf format required by the classification service.

**Key Features:**

* Automatic format conversion
* Metadata preservation
* Correlation ID management
* Error validation

Request Batcher
~~~~~~~~~~~~~~~

.. automodule:: resolver_athena_client.client.transformers.request_batcher
   :members:
   :undoc-members:
   :show-inheritance:

The ``RequestBatcher`` groups multiple images into batches for efficient processing.

**Key Features:**

* Configurable batch sizes
* Timeout-based batching
* Memory-efficient streaming
* Automatic flush on completion

**Example Usage:**

.. code-block:: python

    from resolver_athena_client.client.transformers import RequestBatcher

    batcher = RequestBatcher(batch_size=10, timeout=1.0)
    async for batch in batcher.transform(image_stream):
        # Process batch
        pass

Pipeline Usage
--------------

Transformers can be chained together to create custom processing pipelines:

.. code-block:: python

    from resolver_athena_client.client.transformers import (
        ImageResizer,
        BrotliCompressor,
        ClassificationInputTransformer
    )

    # Create processing pipeline
    resizer = ImageResizer(target_size=(512, 512))
    compressor = BrotliCompressor(quality=6)
    input_transformer = ClassificationInputTransformer(
        deployment_id="your-deployment",
        affiliate="your-affiliate"
    )

    # Process images through pipeline
    async for image_data in image_iterator:
        # Resize image
        resized = await resizer.transform(image_data)

        # Compress data
        compressed = await compressor.transform(resized)

        # Convert to classification input
        classification_input = await input_transformer.transform(compressed)

        # Send for classification
        yield classification_input

Custom Transformers
-------------------

You can create custom transformers by extending the base ``AsyncTransformer`` class:

.. code-block:: python

    from resolver_athena_client.client.transformers.async_transformer import AsyncTransformer
    from resolver_athena_client.client.models import ImageData

    class CustomTransformer(AsyncTransformer):
        """Custom image transformer example."""

        def __init__(self, param1: str, param2: int = 100):
            self.param1 = param1
            self.param2 = param2

        async def transform(self, data: ImageData) -> ImageData:
            """Transform image data with custom logic."""
            # Your custom transformation logic here
            processed_data = self._process_image(data.content)

            return ImageData(
                content=processed_data,
                format=data.format,
                correlation_id=data.correlation_id
            )

        def _process_image(self, image_bytes: bytes) -> bytes:
            """Custom image processing implementation."""
            # Implement your custom processing
            return image_bytes

Performance Considerations
--------------------------

When using transformers:

* **Memory Usage**: Transformers process images in memory. For large batches, consider streaming approaches.
* **CPU Usage**: Image resizing and compression are CPU-intensive. Consider using appropriate batch sizes.
* **Compression Trade-offs**: Higher compression levels reduce bandwidth but increase CPU usage.
* **Pipeline Order**: Order transformers efficiently (e.g., resize before compression).

**Recommended Pipeline Order:**

1. **ImageResizer** - Reduce image size early to minimize processing overhead
2. **Custom transformers** - Apply any custom processing to optimally-sized images
3. **BrotliCompressor** - Compress final image data
4. **ClassificationInputTransformer** - Convert to service format

Error Handling
--------------

Transformers can raise various exceptions during processing:

.. code-block:: python

    from resolver_athena_client.client.exceptions import (
        ImageProcessingError,
        ValidationError
    )

    try:
        transformed = await transformer.transform(image_data)
    except ImageProcessingError as e:
        # Handle image processing failures
        logger.error(f"Image processing failed: {e}")
    except ValidationError as e:
        # Handle validation failures
        logger.error(f"Invalid image data: {e}")

For robust applications, implement retry logic and fallback strategies for transformation failures.

Type Information
----------------

All transformers provide comprehensive type hints:

* Input types: ``ImageData``, ``bytes``, or custom data types
* Output types: ``ImageData``, ``ClassificationInput``, or transformed data
* Async methods: Return ``Awaitable[T]`` where ``T`` is the output type

Configuration
-------------

Transformers accept configuration through their constructors:

**ImageResizer Configuration:**

* ``target_size``: Tuple of (width, height) for output dimensions
* ``resampling``: PIL resampling algorithm (default: ``Image.LANCZOS``)
* ``maintain_aspect_ratio``: Whether to preserve aspect ratio (default: ``True``)

**BrotliCompressor Configuration:**

* ``quality``: Compression quality level 0-11 (default: 6)
* ``window_bits``: Compression window size (default: 22)

**RequestBatcher Configuration:**

* ``batch_size``: Maximum items per batch (default: 10)
* ``timeout``: Maximum time to wait for batch completion (default: 1.0)

See individual transformer documentation for complete configuration options.
