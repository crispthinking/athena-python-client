Installation Guide
=================

This guide will walk you through the process of installing the Athena Client library.

Prerequisites
------------

Before installing Athena Client, ensure you have:

* Python 3.8 or higher
* uv package manager (recommended) or pip

Installation Methods
------------------

Using uv (Recommended)
~~~~~~~~~~~~~~~~~~~~~

The recommended way to install Athena Client is using ``uv``:

.. code-block:: bash

   uv sync --dev

This will install all dependencies including development packages.

Using pip
~~~~~~~~~

Alternatively, you can install using pip:

.. code-block:: bash

   pip install athena-client

Development Installation
----------------------

For development purposes, you'll want to install additional dependencies:

1. Clone the repository:

   .. code-block:: bash

      git clone https://github.com/yourusername/athena-client.git
      cd athena-client

2. Install dependencies:

   .. code-block:: bash

      uv sync --dev

3. Install git hooks:

   .. code-block:: bash

      pre-commit install

4. Compile protobufs (run from root):

   .. code-block:: bash

      bash scripts/compile_proto.sh

Verification
-----------

To verify your installation:

1. Run the tests:

   .. code-block:: bash

      pytest

2. Check type hints:

   .. code-block:: bash

      pyright

3. Run linting:

   .. code-block:: bash

      ruff check

Next Steps
---------

Once installed, you can:

* Read the :doc:`examples` guide to begin using Athena Client
* Check out the :doc:`api/index` documentation
* Check out the examples section for common use cases

Troubleshooting
--------------

If you encounter any issues during installation:

1. Ensure you have the correct Python version
2. Update your package managers:

   .. code-block:: bash

      uv pip install --upgrade pip
      uv pip install --upgrade uv

3. Check that all dependencies are properly installed:

   .. code-block:: bash

      uv sync --check

For more help, please:

* Check the project's GitHub Issues
* Review the contributing guide for common development issues
* Reach out to the maintainers if you need additional assistance
