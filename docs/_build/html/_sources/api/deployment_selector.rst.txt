Deployment Selector
==================

The deployment selector provides functionality for discovering and selecting Athena service deployments. It abstracts the complexities of deployment management and provides a simple interface for listing and validating deployments.

.. module:: athena_client.client.deployment_selector

.. autoclass:: DeploymentSelector
   :members:
   :special-members: __aenter__, __aexit__
   :show-inheritance:

Usage
-------------------

The deployment selector is typically used as an async context manager to ensure proper resource cleanup::

    async with DeploymentSelector(channel) as selector:
        # List available deployments
        deployments = await selector.list_deployments()

        # Select a specific deployment
        deployment_id = deployments[0].id

        # Use deployment_id with AthenaClient...

Best Practices
--------------

- Always use the deployment selector as an async context manager to ensure proper cleanup
- Cache deployment information when appropriate to reduce API calls
- Validate deployment IDs before using them with the client
- Handle deployment-related exceptions appropriately

Error Handling
----------------------

The deployment selector may raise the following exceptions:

- ``grpc.aio.AioRpcError``: For GRPC-level communication errors
- ``ValueError``: For invalid deployment IDs or configurations
- ``RuntimeError``: For unexpected state or implementation errors
