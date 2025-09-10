Installation Guide
==================

This guide will walk you through installing and setting up the Athena Client library for both development and production use.

Prerequisites
-------------

Before installing Athena Client, ensure you have:

* Python 3.10 or higher
* `uv <https://docs.astral.sh/uv/>`_ package manager (recommended)
* Git (for development installation)

Production Installation
-----------------------

Using uv (Recommended)
~~~~~~~~~~~~~~~~~~~~~~

The recommended way to install Athena Client for production use:

.. code-block:: bash

   uv add athena-client

Using pip
~~~~~~~~~

Alternatively, you can install using pip:

.. code-block:: bash

   pip install athena-client

Development Installation
------------------------

For development, you'll need to clone the repository and install with development dependencies.

1. Clone the repository:

   .. code-block:: bash

      git clone <repository-url>
      cd athena-client

2. Install dependencies with uv:

   .. code-block:: bash

      uv sync --dev

   This installs all dependencies including development tools like pytest, ruff, pyright, and pre-commit.

3. Install git hooks for code quality:

   .. code-block:: bash

      pre-commit install

4. Compile protocol buffers (required for development):

   .. code-block:: bash

      bash scripts/compile_proto.sh

Development Commands
--------------------

Once installed for development, you can use these commands:

Build and Test
~~~~~~~~~~~~~~

.. code-block:: bash

   # Build the package
   uv build

   # Run the full test suite
   pytest

   # Run specific tests
   pytest path/to/test.py

   # Run tests by pattern
   pytest -k "test_name"

   # Run tests with coverage
   pytest --cov=src/athena_client

Code Quality
~~~~~~~~~~~~

.. code-block:: bash

   # Type check code
   pyright

   # Format code
   ruff format

   # Lint code
   ruff check

   # Fix auto-fixable lint issues
   ruff check --fix

Documentation
~~~~~~~~~~~~~

.. code-block:: bash

   # Build documentation
   cd docs && make clean && make html

   # View documentation locally
   open docs/_build/html/index.html

Verification
------------

To verify your installation works correctly:

1. **Check the installation**:

   .. code-block:: python

      import resolver_athena_client
      print(resolver_athena_client.__version__)

2. **Run the test suite**:

   .. code-block:: bash

      pytest

3. **Verify type checking**:

   .. code-block:: bash

      pyright

4. **Check code formatting**:

   .. code-block:: bash

      ruff check

Environment Setup
-----------------

For development and testing, you'll typically need these environment variables:

.. code-block:: bash

   # OAuth credentials
   export OAUTH_CLIENT_ID="your-client-id"
   export OAUTH_CLIENT_SECRET="your-client-secret"

   # Athena service configuration
   export ATHENA_HOST="your-athena-host"

   # Optional OAuth configuration
   export OAUTH_AUTH_URL="https://crispthinking.auth0.com/oauth/token"
   export OAUTH_AUDIENCE="crisp-athena-dev"

You can create a `.env` file in the project root with these variables, and the examples will automatically load them using `python-dotenv`.

Troubleshooting
---------------

Common Installation Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~

**uv not found**:
   Install uv following the `official installation guide <https://docs.astral.sh/uv/getting-started/installation/>`_.

**Python version mismatch**:
   Ensure you have Python 3.10 or higher. Check with:

   .. code-block:: bash

      python --version

**Protocol buffer compilation fails**:
   Ensure you have the required dependencies and run:

   .. code-block:: bash

      uv sync --dev
      bash scripts/compile_proto.sh

**Pre-commit hooks failing**:
   The hooks will automatically format and check your code. If they fail:

   .. code-block:: bash

      # Fix formatting issues
      ruff format

      # Fix lint issues
      ruff check --fix

      # Run type checking
      pyright

Development Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~

The development installation includes these key tools:

* **pytest**: Testing framework with async support and coverage
* **ruff**: Fast linting and formatting
* **pyright**: Type checking
* **pre-commit**: Git hooks for code quality
* **sphinx**: Documentation generation
* **mypy-protobuf**: Type hints for protocol buffers

Next Steps
----------

Once installed, you can:

* Read the :doc:`examples` guide to see usage patterns
* Check the :doc:`authentication` guide for setup instructions
* Browse the :doc:`api/index` documentation for detailed API reference
* Review the :doc:`development` guide for contribution guidelines

For questions or issues:

* Check the project's GitHub Issues
* Review the :doc:`contributing` guide
* See the examples in the ``examples/`` directory
