Error Handling
==============

.. currentmodule:: athena_client.client.exceptions

The exceptions module provides a comprehensive hierarchy of exception types for handling various error conditions that can occur when using the Athena Client library.

Exception Hierarchy
~~~~~~~~~~~~~~~~~~~~

All Athena Client exceptions inherit from the base ``AthenaError`` class, providing a consistent error handling interface.

Base Exception
~~~~~~~~~~~~~~

.. autoexception:: AthenaError
   :members:
   :show-inheritance:

   Base class for all Athena exceptions. All other exceptions in the library inherit from this class.

Request and Response Errors
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoexception:: InvalidRequestError
   :members:
   :show-inheritance:

   Raised when the request data is invalid or malformed.

.. autoexception:: InvalidResponseError
   :members:
   :show-inheritance:

   Raised when the response from the service is invalid or cannot be parsed.

Authentication Errors
~~~~~~~~~~~~~~~~~~~~~

.. autoexception:: InvalidAuthError
   :members:
   :show-inheritance:

   Raised when authentication credentials are invalid or missing.

.. autoexception:: OAuthError
   :members:
   :show-inheritance:

   Raised when OAuth authentication fails.

.. autoexception:: TokenExpiredError
   :members:
   :show-inheritance:

   Raised when the authentication token has expired and needs to be refreshed.

.. autoexception:: CredentialError
   :members:
   :show-inheritance:

   Raised when there are issues with credential management or retrieval.

Connection Errors
~~~~~~~~~~~~~~~~~

.. autoexception:: InvalidHostError
   :members:
   :show-inheritance:

   Raised when the host configuration is invalid or empty.

Classification Errors
~~~~~~~~~~~~~~~~~~~~~

.. autoexception:: ClassificationOutputError
   :members:
   :show-inheritance:

   Raised when an individual classification output contains an error. This exception
   includes detailed information about the specific failure.

Usage Examples
--------------

Basic Error Handling
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from athena_client.client.exceptions import (
        AthenaError,
        InvalidAuthError,
        InvalidRequestError
    )

    try:
        async with AthenaClient(channel, options) as client:
            results = client.classify_images(image_iterator)
            async for result in results:
                # Process results
                pass
    except InvalidAuthError as e:
        logger.error(f"Authentication failed: {e}")
        # Handle authentication error
    except InvalidRequestError as e:
        logger.error(f"Invalid request: {e}")
        # Handle request validation error
    except AthenaError as e:
        logger.error(f"Athena client error: {e}")
        # Handle any other Athena-specific error
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        # Handle unexpected errors

OAuth Error Handling
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from athena_client.client.exceptions import (
        OAuthError,
        TokenExpiredError,
        CredentialError
    )

    try:
        credential_helper = CredentialHelper(
            client_id=client_id,
            client_secret=client_secret
        )
        token = await credential_helper.get_token()
    except OAuthError as e:
        logger.error(f"OAuth authentication failed: {e}")
        # Handle OAuth failure - check credentials
    except TokenExpiredError as e:
        logger.error(f"Token expired: {e}")
        # Handle token expiration - will auto-refresh
    except CredentialError as e:
        logger.error(f"Credential error: {e}")
        # Handle credential management issues

Classification Error Handling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from athena_client.client.exceptions import ClassificationOutputError
    from athena_client.client.utils import process_classification_outputs

    try:
        async for result in results:
            # Process outputs with error handling
            successful_outputs = process_classification_outputs(
                result,
                raise_on_error=False,
                log_errors=True
            )

            for output in successful_outputs:
                # Handle successful classifications
                pass

    except ClassificationOutputError as e:
        logger.error(
            f"Classification failed for {e.correlation_id}: "
            f"{e.error_message} (code: {e.error_code})"
        )
        if e.error_details:
            logger.error(f"Error details: {e.error_details}")

Connection Error Handling
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from athena_client.client.exceptions import InvalidHostError
    import asyncio

    try:
        channel = create_channel(host=host, auth_token=token)

    except InvalidHostError as e:
        logger.error(f"Invalid host configuration: {e}")
        # Handle host configuration error

    except ConnectionError as e:
        logger.error(f"Connection failed: {e}")
        # Handle network connection issues

    except asyncio.TimeoutError as e:
        logger.error(f"Connection timeout: {e}")
        # Handle connection timeouts

Error Recovery Strategies
-------------------------

Retry Logic
~~~~~~~~~~~

.. code-block:: python

    import asyncio
    from athena_client.client.exceptions import (
        AthenaError,
        TokenExpiredError,
        InvalidRequestError
    )

    async def classify_with_retry(client, image_iterator, max_retries=3):
        """Classify images with automatic retry logic."""
        for attempt in range(max_retries):
            try:
                results = client.classify_images(image_iterator)
                async for result in results:
                    yield result
                break  # Success, exit retry loop

            except TokenExpiredError:
                # Token expired, credential helper will auto-refresh
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0)
                    continue
                raise

            except InvalidRequestError:
                # Don't retry on invalid requests
                raise

            except AthenaError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    await asyncio.sleep(2.0 ** attempt)  # Exponential backoff
                    continue
                raise

Graceful Degradation
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from athena_client.client.exceptions import AthenaError

    async def classify_with_fallback(client, image_iterator, fallback_handler=None):
        """Classify images with fallback handling."""
        try:
            results = client.classify_images(image_iterator)
            async for result in results:
                yield result

        except AthenaError as e:
            logger.error(f"Classification service failed: {e}")

            if fallback_handler:
                logger.info("Using fallback classification method")
                async for fallback_result in fallback_handler(image_iterator):
                    yield fallback_result
            else:
                logger.error("No fallback available, propagating error")
                raise

Best Practices
--------------

1. **Specific Exception Handling**: Catch specific exception types rather than using broad exception handlers when possible.

2. **Error Logging**: Always log errors with sufficient context for debugging.

3. **Retry Logic**: Implement appropriate retry logic for transient errors like network issues or token expiration.

4. **Graceful Degradation**: Consider fallback strategies for critical applications.

5. **Error Context**: When re-raising exceptions, preserve the original context using ``raise ... from e``.

6. **Resource Cleanup**: Use async context managers to ensure proper cleanup even when exceptions occur.

Common Error Scenarios
----------------------

Authentication Issues
~~~~~~~~~~~~~~~~~~~~~

* **Invalid credentials**: Check ``OAUTH_CLIENT_ID`` and ``OAUTH_CLIENT_SECRET``
* **Token expiration**: The credential helper handles this automatically
* **Permission denied**: Verify your credentials have the necessary permissions

Connection Problems
~~~~~~~~~~~~~~~~~~~

* **Invalid host**: Verify the ``ATHENA_HOST`` environment variable
* **Network timeouts**: Adjust timeout settings or check network connectivity
* **Service unavailable**: Implement retry logic with exponential backoff

Request Validation
~~~~~~~~~~~~~~~~~~

* **Invalid image data**: Ensure images are in supported formats
* **Missing required fields**: Check that all required configuration is provided
* **Invalid deployment ID**: Verify the deployment exists and is accessible

See Also
--------

* :doc:`client` - Main client interface and error handling patterns
* :doc:`../authentication` - Authentication setup and troubleshooting
* :doc:`../examples` - Complete examples with error handling
