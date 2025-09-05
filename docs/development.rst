Development Guide
=================

This guide covers development setup, coding standards, testing practices, and contribution guidelines for the Athena Client library.

Development Setup
-----------------

Prerequisites
~~~~~~~~~~~~~

* Python 3.10 or higher
* `uv <https://docs.astral.sh/uv/>`_ package manager
* Git
* Pre-commit (installed via uv)

Initial Setup
~~~~~~~~~~~~~

1. **Clone the repository**:

   .. code-block:: bash

      git clone <repository-url>
      cd athena-client

2. **Install dependencies**:

   .. code-block:: bash

      uv sync --dev

3. **Install pre-commit hooks**:

   .. code-block:: bash

      pre-commit install

4. **Compile protocol buffers**:

   .. code-block:: bash

      bash scripts/compile_proto.sh

5. **Verify setup**:

   .. code-block:: bash

      pytest
      pyright
      ruff check

Project Structure
-----------------

.. code-block::

   athena-client/
   ├── src/athena_client/           # Main source code
   │   ├── client/                  # Client implementation
   │   │   ├── models/              # Data models
   │   │   ├── streaming/           # Streaming components
   │   │   └── transformers/        # Image processing pipeline
   │   ├── generated/               # Generated protobuf code
   │   └── grpc_wrappers/           # gRPC integration
   ├── tests/                       # Test suite
   ├── examples/                    # Usage examples
   ├── docs/                        # Sphinx documentation
   ├── scripts/                     # Build and utility scripts
   └── athena-protobufs/            # Protocol buffer definitions (submodule)

Development Commands
--------------------

Package Management
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Install all dependencies
   uv sync --dev

   # Add a new dependency
   uv add package-name

   # Add a development dependency
   uv add --dev package-name

   # Build the package
   uv build

Testing
~~~~~~~

.. code-block:: bash

   # Run all tests
   pytest

   # Run specific test file
   pytest tests/test_client.py

   # Run tests with pattern matching
   pytest -k "test_oauth"

   # Run tests with coverage
   pytest --cov=src/athena_client

   # Run tests with coverage report
   pytest --cov=src/athena_client --cov-report=html

Code Quality
~~~~~~~~~~~~

.. code-block:: bash

   # Format code
   ruff format

   # Check code style and fix auto-fixable issues
   ruff check --fix

   # Type checking
   pyright

   # Run all quality checks
   ruff format && ruff check && pyright

Documentation
~~~~~~~~~~~~~

.. code-block:: bash

   # Build documentation
   cd docs && make clean && make html

   # View documentation
   open docs/_build/html/index.html

   # Watch for changes (if sphinx-autobuild is installed)
   cd docs && sphinx-autobuild . _build/html

Protocol Buffers
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Compile protocol buffers
   bash scripts/compile_proto.sh

   # Update submodule (if protobuf definitions change)
   git submodule update --remote

Coding Standards
----------------

Python Style
~~~~~~~~~~~~

The project follows these coding standards:

* **Type hints**: Required for all public APIs and recommended for internal code
* **Docstrings**: Google-style docstrings for all public functions and classes
* **Formatting**: Black-compatible formatting via ruff
* **Line length**: 80 characters maximum
* **Import organization**: isort-compatible import sorting

Example function with proper style:

.. code-block:: python

   async def classify_images(
       self,
       image_iterator: AsyncIterator[bytes],
       *,
       correlation_id: str | None = None,
   ) -> AsyncIterator[ClassificationResult]:
       """Classify a stream of images.

       Args:
           image_iterator: Async iterator yielding image data as bytes
           correlation_id: Optional correlation ID for request tracing

       Returns:
           Async iterator of classification results

       Raises:
           AthenaClientError: If classification fails
           ConnectionError: If connection to service fails

       Example:
           >>> async with AthenaClient(channel, options) as client:
           ...     results = client.classify_images(image_iterator)
           ...     async for result in results:
           ...         print(result.outputs)
       """

Async Patterns
~~~~~~~~~~~~~~

The codebase uses async/await throughout:

* **Async context managers**: For resource management
* **Async iterators**: For streaming data processing
* **Async generators**: For pipeline transformations
* **Proper cleanup**: Using try/finally or async context managers

.. code-block:: python

   # Good: Async context manager with proper cleanup
   async with AthenaClient(channel, options) as client:
       async for result in client.classify_images(images):
           # Process results
           pass

   # Good: Async generator for transformations
   async def transform_images(
       image_iterator: AsyncIterator[bytes]
   ) -> AsyncIterator[ProcessedImage]:
       async for image_data in image_iterator:
           processed = await process_image(image_data)
           yield processed

Error Handling
~~~~~~~~~~~~~~

Use structured error handling with custom exception types:

.. code-block:: python

   from athena_client.client.exceptions import AthenaClientError

   try:
       result = await client.classify_image(image_data)
   except AthenaClientError as e:
       logger.error(f"Classification failed: {e}")
       # Handle specific client errors
   except Exception as e:
       logger.exception("Unexpected error")
       # Handle unexpected errors

Testing Guidelines
------------------

Test Structure
~~~~~~~~~~~~~~

* **Location**: All tests in ``tests/`` directory
* **Naming**: Test files start with ``test_``
* **Organization**: Mirror the source code structure

.. code-block::

   tests/
   ├── test_client.py              # Client tests
   ├── test_authentication.py     # Auth tests
   ├── test_transformers.py       # Pipeline tests
   └── integration/               # Integration tests
       └── test_end_to_end.py

Test Categories
~~~~~~~~~~~~~~~

**Unit Tests**:
   * Test individual functions and classes
   * Mock external dependencies
   * Fast execution (< 1 second each)

**Integration Tests**:
   * Test component interactions
   * May use real services in test mode
   * Slower execution acceptable

**End-to-End Tests**:
   * Test complete workflows
   * Use real services when possible
   * Mark with ``@pytest.mark.e2e``

Writing Tests
~~~~~~~~~~~~~

Use pytest with async support:

.. code-block:: python

   import pytest
   from unittest.mock import AsyncMock, Mock
   from athena_client.client.athena_client import AthenaClient

   @pytest.fixture
   async def mock_channel():
       """Create a mock gRPC channel."""
       return Mock()

   @pytest.fixture
   def client_options():
       """Create test client options."""
       return AthenaOptions(
           host="test-host",
           deployment_id="test-deployment",
           resize_images=True,
       )

   @pytest.mark.asyncio
   async def test_client_classification(mock_channel, client_options):
       """Test basic client classification."""
       async with AthenaClient(mock_channel, client_options) as client:
           # Test implementation
           pass

   @pytest.mark.asyncio
   async def test_authentication_failure():
       """Test authentication error handling."""
       with pytest.raises(AuthenticationError):
           # Test that should raise AuthenticationError
           pass

Mocking Guidelines
~~~~~~~~~~~~~~~~~~

* **Mock external services**: Don't make real API calls in unit tests
* **Use AsyncMock**: For async functions and context managers
* **Test both success and failure**: Cover error paths
* **Verify interactions**: Check that mocks were called correctly

.. code-block:: python

   @pytest.mark.asyncio
   async def test_credential_helper_token_refresh():
       """Test automatic token refresh."""
       mock_http_client = AsyncMock()
       mock_http_client.post.return_value.json.return_value = {
           "access_token": "new-token",
           "expires_in": 3600
       }

       credential_helper = CredentialHelper(
           client_id="test-id",
           client_secret="test-secret",
           http_client=mock_http_client
       )

       token = await credential_helper.get_token()
       assert token == "new-token"
       mock_http_client.post.assert_called_once()

Documentation Standards
-----------------------

Documentation Types
~~~~~~~~~~~~~~~~~~~

* **API Documentation**: Auto-generated from docstrings
* **User Guides**: High-level usage documentation
* **Examples**: Working code examples
* **Development Docs**: This guide and contribution instructions

Docstring Format
~~~~~~~~~~~~~~~~

Use Google-style docstrings:

.. code-block:: python

   def process_image(image_data: bytes, *, resize: bool = True) -> ProcessedImage:
       """Process image data for classification.

       This function resizes, compresses, and validates image data before
       sending it for classification.

       Args:
           image_data: Raw image data as bytes
           resize: Whether to resize image to optimal dimensions

       Returns:
           Processed image ready for classification

       Raises:
           ValueError: If image data is invalid
           ProcessingError: If image processing fails

       Example:
           >>> image_data = load_image("photo.jpg")
           >>> processed = process_image(image_data, resize=True)
           >>> print(f"Processed size: {len(processed.data)}")
       """

Building Documentation
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Install documentation dependencies
   uv sync --group docs

   # Build HTML documentation
   cd docs
   make clean
   make html

   # View the documentation
   open _build/html/index.html

Contribution Workflow
---------------------

Making Changes
~~~~~~~~~~~~~~

1. **Create a feature branch**:

   .. code-block:: bash

      git checkout -b feature/your-feature-name

2. **Make your changes** following the coding standards

3. **Add tests** for new functionality

4. **Update documentation** if needed

5. **Run quality checks**:

   .. code-block:: bash

      ruff format
      ruff check
      pyright
      pytest

6. **Commit your changes**:

   .. code-block:: bash

      git add .
      git commit -m "feat: add new feature"

Pull Request Guidelines
~~~~~~~~~~~~~~~~~~~~~~~

* **Title format**: ``[component] Description`` (e.g., ``[client] Add OAuth support``)
* **Description**: Clear description of changes and motivation
* **Tests**: Include tests for new functionality
* **Documentation**: Update docs for API changes
* **Quality checks**: Ensure all checks pass
* **Single focus**: Keep PRs focused on one change

Commit Message Format
~~~~~~~~~~~~~~~~~~~~~

Use conventional commit format:

.. code-block::

   type(scope): description

   [optional body]

   [optional footer]

**Types**:
* ``feat``: New feature
* ``fix``: Bug fix
* ``docs``: Documentation changes
* ``test``: Test changes
* ``refactor``: Code refactoring
* ``style``: Code style changes
* ``chore``: Maintenance tasks

**Examples**:

.. code-block::

   feat(client): add OAuth credential helper
   fix(auth): handle token refresh failures
   docs(api): update authentication examples
   test(client): add integration tests for streaming

Pre-commit Hooks
~~~~~~~~~~~~~~~~

The project uses pre-commit hooks to ensure code quality:

* **ruff**: Code formatting and linting
* **pyright**: Type checking
* **conventional-commits**: Commit message validation

If hooks fail, fix the issues and commit again:

.. code-block:: bash

   # Fix formatting issues
   ruff format

   # Fix linting issues
   ruff check --fix

   # Check types
   pyright

   # Commit again
   git add .
   git commit -m "fix: resolve linting issues"

Release Process
---------------

Version Management
~~~~~~~~~~~~~~~~~~

The project uses semantic versioning (SemVer):

* **Major** (1.0.0): Breaking changes
* **Minor** (0.1.0): New features, backward compatible
* **Patch** (0.0.1): Bug fixes, backward compatible

Creating Releases
~~~~~~~~~~~~~~~~~

1. **Update version** in ``pyproject.toml``
2. **Update changelog** with release notes
3. **Create release tag**:

   .. code-block:: bash

      git tag -a v0.1.0 -m "Release v0.1.0"
      git push origin v0.1.0

4. **Build and publish**:

   .. code-block:: bash

      uv build
      # Publish to PyPI (if configured)

Debugging and Troubleshooting
------------------------------

Common Development Issues
~~~~~~~~~~~~~~~~~~~~~~~~~

**Protocol buffer compilation fails**:
   * Ensure all dependencies are installed: ``uv sync --dev``
   * Check that the submodule is up to date: ``git submodule update --init``

**Type checking errors**:
   * Ensure pyright is configured correctly
   * Check that generated code is excluded: see ``pyproject.toml``

**Test failures**:
   * Run tests individually to isolate issues
   * Check mock setup and assertions
   * Verify async test patterns

**Import errors in tests**:
   * Ensure the package is installed in development mode
   * Check that ``__init__.py`` files are present

Debug Configuration
~~~~~~~~~~~~~~~~~~~

Enable debug logging for development:

.. code-block:: python

   import logging

   # Enable debug logging
   logging.basicConfig(
       level=logging.DEBUG,
       format="%(asctime)s.%(msecs)03d %(levelname)s [%(name)s]: %(message)s",
       datefmt="%H:%M:%S"
   )

   # Set specific logger levels
   logging.getLogger("athena_client").setLevel(logging.DEBUG)
   logging.getLogger("grpc").setLevel(logging.INFO)

Performance Profiling
~~~~~~~~~~~~~~~~~~~~~~

For performance analysis:

.. code-block:: python

   import cProfile
   import pstats

   # Profile code execution
   profiler = cProfile.Profile()
   profiler.enable()

   # Your code here
   await your_function()

   profiler.disable()

   # Analyze results
   stats = pstats.Stats(profiler)
   stats.sort_stats('cumulative')
   stats.print_stats(20)

Getting Help
------------

If you encounter issues during development:

1. **Check the documentation**: Review relevant sections
2. **Search existing issues**: Look for similar problems on GitHub
3. **Enable debug logging**: Get more detailed error information
4. **Ask for help**: Create an issue with detailed information

For questions about:

* **Setup issues**: See :doc:`installation`
* **Usage patterns**: See :doc:`examples`
* **API details**: See :doc:`api/index`
* **Authentication**: See :doc:`authentication`

Contributing Checklist
-----------------------

Before submitting a pull request:

- [ ] Code follows project style guidelines
- [ ] All tests pass (``pytest``)
- [ ] Type checking passes (``pyright``)
- [ ] Code is formatted (``ruff format``)
- [ ] Linting passes (``ruff check``)
- [ ] Documentation is updated for API changes
- [ ] Tests are added for new functionality
- [ ] Commit messages follow conventional format
- [ ] Pre-commit hooks are installed and passing

This ensures high code quality and smooth collaboration.
