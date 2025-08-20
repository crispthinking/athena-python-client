Contributing Guide
================

This guide will help you get started with contributing to the Athena Client project.

Development Setup
---------------

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

4. Compile protobufs (from project root):

   .. code-block:: bash

      bash scripts/compile_proto.sh

Development Workflow
------------------

Code Style
~~~~~~~~~

- Use Python type hints throughout
- Follow Black formatting (via ruff)
- Use async/await for I/O operations
- Document public APIs with docstrings
- Use functional patterns where possible
- Implement proper error handling

Testing
~~~~~~~

Tests are located in the ``tests/`` directory. To run tests:

.. code-block:: bash

   # Run all tests
   pytest

   # Run specific test file
   pytest path/to/test.py

   # Run tests matching pattern
   pytest -k "test_name"

   # Run with coverage
   pytest --cov=src/athena_client

Type Checking
~~~~~~~~~~~

Use ``pyright`` for type checking:

.. code-block:: bash

   pyright

Code Formatting
~~~~~~~~~~~~~

Format code using ``ruff format``:

.. code-block:: bash

   ruff format

Linting
~~~~~~

Run the linter using ``ruff check``:

.. code-block:: bash

   ruff check

Pull Request Process
------------------

1. Create a new branch for your changes:

   .. code-block:: bash

      git checkout -b feature/your-feature-name

2. Make your changes, following our code style guidelines

3. Run all checks before committing:

   .. code-block:: bash

      ruff check
      pyright
      pytest

4. Commit your changes with a descriptive message:

   .. code-block:: bash

      git commit -m "[component] Description of changes"

5. Push your changes and create a pull request

6. Update your PR based on review feedback

Documentation
------------

- Update documentation for API changes
- Add docstrings for new functions and classes
- Update example code as needed
- Add comments for complex logic

Best Practices
------------

- Keep PRs focused on a single change
- Write meaningful commit messages
- Add tests for new functionality
- Update documentation as needed
- Handle errors appropriately
- Use correlation IDs for request tracing

Common Tasks
----------

Updating Dependencies
~~~~~~~~~~~~~~~~~~

To update project dependencies:

.. code-block:: bash

   uv sync --upgrade

Regenerating Protobufs
~~~~~~~~~~~~~~~~~~~~

After updating protobuf definitions:

.. code-block:: bash

   bash scripts/compile_proto.sh

Getting Help
----------

If you need help:

- Check existing GitHub issues
- Read the :doc:`api/index` documentation
- Review the :doc:`examples`
- Contact the maintainers

Code Review Guidelines
-------------------

When reviewing code:

1. Check for type hints
2. Verify test coverage
3. Ensure documentation is updated
4. Look for error handling
5. Verify style compliance
6. Check performance implications
7. Review security considerations
