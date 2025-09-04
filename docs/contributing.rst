Contributing to Athena Client
=============================

We welcome contributions to the Athena Client library! This guide will help you get started with contributing code, documentation, bug reports, and feature requests.

Getting Started
---------------

Setting Up Development Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Fork the repository** on GitHub

2. **Clone your fork**:

   .. code-block:: bash

      git clone https://github.com/your-username/athena-client.git
      cd athena-client

3. **Add upstream remote**:

   .. code-block:: bash

      git remote add upstream https://github.com/original-org/athena-client.git

4. **Install dependencies**:

   .. code-block:: bash

      uv sync --dev

5. **Install pre-commit hooks**:

   .. code-block:: bash

      pre-commit install

6. **Compile protocol buffers**:

   .. code-block:: bash

      bash scripts/compile_proto.sh

7. **Verify your setup**:

   .. code-block:: bash

      pytest
      pyright
      ruff check

Contributions
----------------------

Bug Reports
~~~~~~~~~~~

When reporting bugs, please include:

* **Clear description** of the issue
* **Steps to reproduce** the problem
* **Expected behavior** vs actual behavior
* **Environment details** (Python version, OS, etc.)
* **Code examples** demonstrating the issue
* **Error messages** and stack traces

Use this template:

.. code-block::

   **Bug Description**
   A clear description of what the bug is.

   **To Reproduce**
   Steps to reproduce the behavior:
   1. Create client with options '...'
   2. Call method '...'
   3. See error

   **Expected Behavior**
   What you expected to happen.

   **Environment**
   - Python version: 3.11
   - athena-client version: 0.1.0
   - OS: macOS 13.0

   **Additional Context**
   Any other relevant information.

Development Workflow
--------------------

Creating a Pull Request
~~~~~~~~~~~~~~~~~~~~~~~

1. **Create a feature branch**:

   .. code-block:: bash

      git checkout -b feature/your-feature-name

2. **Make your changes** following our guidelines

3. **Write tests** for new functionality:

   .. code-block:: bash

      # Add tests to appropriate test files
      # Run tests to ensure they pass
      pytest tests/test_your_feature.py

4. **Update documentation** if needed:

   .. code-block:: bash

      # Update relevant .rst files
      # Build docs to check formatting
      cd docs && make html

5. **Run quality checks**:

   .. code-block:: bash

      ruff format         # Format code
      ruff check          # Check linting
      pyright             # Type checking
      pytest              # Run tests

6. **Commit your changes**:

   .. code-block:: bash

      git add .
      git commit -m "feat: add your feature description"

7. **Push to your fork**:

   .. code-block:: bash

      git push origin feature/your-feature-name

8. **Create pull request** on GitHub
