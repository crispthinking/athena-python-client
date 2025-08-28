GRPC Wrappers
=============

The GRPC wrappers module provides low-level components for interacting with the
Athena service via GRPC. These are consumed by the higher-level clients, you
should only use them directly if you are implementing a new client.

// TODO -- write GRPC docs.
See the protobuf documentation for more information.

.. module:: athena_client.grpc_wrappers

Service Clients
---------------

.. autoclass:: athena_client.grpc_wrappers.classifier_service.ClassifierServiceClient
   :members:
   :special-members: __init__
   :show-inheritance:

The ClassifierServiceClient provides direct access to Athena service methods::

    client = ClassifierServiceClient(channel)
    deployment_response = await client.get_deployment(request)
    classify_response = await client.classify(request)
