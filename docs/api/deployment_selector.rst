Deployment Selector
===================

The deployment selector provides functionality for discovering and selecting
Athena service deployments. It abstracts the complexities of deployment
management and provides a simple interface for listing deployments.

.. module:: athena_client.client.deployment_selector

.. autoclass:: DeploymentSelector
   :members:
   :special-members: __init__
   :show-inheritance:
   :no-index:

Usage
~~~~~

The deployment selector is typically used as an async context manager to ensure
proper resource cleanup::

    async with DeploymentSelector(channel) as selector:
        # List available deployments
        deployments = await selector.list_deployments()

        # Select a specific deployment
        deployment_id = deployments[0].id

        # Use deployment_id with AthenaClient...

Best Practices
~~~~~~~~~~~~~~

- Use the deployment selector as an async context manager to ensure proper cleanup
- Cache deployment information when appropriate to reduce API calls
