Generated API Documentation
=========================

This directory contains automatically generated API documentation from source code.
**Do not edit these files directly** as they will be overwritten when the documentation is rebuilt.

Instead:

1. Edit the docstrings in the source code
2. Update the API documentation structure in the RST files in the parent directory
3. Rebuild the documentation using ``make html``

File Structure
-------------

The generated documentation follows this structure:

- ``athena_client.client.*`` - Core client documentation
- ``athena_client.client.exceptions.*`` - Exception class documentation
- ``athena_client.client.transformers.*`` - Data transformation utilities
- ``athena_client.client.correlation.*`` - Correlation ID management
- ``athena_client.client.deployment_selector.*`` - Deployment selection functionality

Regenerating Documentation
------------------------

To rebuild the API documentation:

1. Edit source code docstrings as needed
2. From the docs directory, run:

   .. code-block:: bash

      make clean
      make html

3. The documentation will be regenerated in this directory
