GRPC Wrappers
=============

The GRPC wrappers module provides low-level components for interacting with the Athena service via GRPC.

.. module:: athena_client.grpc_wrappers

Channel Management
----------------

.. autoclass:: athena_client.grpc_wrappers.channel.Channel
   :members:
   :special-members: __aenter__, __aexit__
   :show-inheritance:

The Channel class manages GRPC channel lifecycle and configuration::

    async with Channel(endpoint) as channel:
        # Channel is initialized and ready for use
        ...
        # Channel is automatically closed on context exit

Service Clients
---------------

.. autoclass:: athena_client.grpc_wrappers.classifier_service.ClassifierServiceClient
   :members:
   :special-members: __init__
   :show-inheritance:

The ClassifierServiceClient provides direct access to Athena service methods::

    client = ClassifierServiceClient(channel)
    response = await client.classify(request)

Error Handling
--------------

GRPC wrappers may raise the following exceptions:

- ``grpc.aio.AioRpcError``: For GRPC-level communication errors
- ``ValueError``: For invalid configurations or parameters
- ``RuntimeError``: For unexpected states or implementation errors

All GRPC errors include:

- Status codes indicating the type of failure
- Detailed error messages
- Metadata about the failed request

Best Practices
--------------

When using GRPC wrappers:

- Always use channels with async context managers
- Handle GRPC errors appropriately
- Monitor channel health and connectivity
- Configure appropriate timeouts and retries
- Use proper error handling and logging

Protocol Buffers
--------------

The module integrates with generated protocol buffer code:

- Request and response message types
- Service definitions and stubs
- Enumeration types and constants

For example::

    from athena_client.generated.athena import athena_pb2

    request = athena_pb2.ClassifyRequest(
        deployment_id="my-deployment",
        inputs=[...],
    )
