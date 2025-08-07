"""Low-level GRPC client for the ClassifierService."""

import grpc
from google.protobuf.empty_pb2 import Empty

from athena_client.generated.athena.athena_pb2 import (
    Classification,
    ClassificationInput,
    ClassificationOutput,
    ClassifyRequest,
    ClassifyResponse,
    Deployment,
    ListDeploymentsResponse,
    RequestEncoding,
)
from athena_client.generated.athena.athena_pb2_grpc import ClassifierServiceStub


class ClassifierServiceClient:
    """Low-level gRPC wrapper for the ClassifierService."""

    def __init__(self, channel: grpc.Channel) -> None:
        """Initialize the client with a gRPC channel.

        Args:
            channel (grpc.aio.Channel): A gRPC channel to communicate with the
            server.

        """
        self.stub = ClassifierServiceStub(channel)

    def classify(self, request: ClassifyRequest) -> ClassifyResponse:
        """Perform image classification in a deployment-based streaming context.

        Args:
            request (ClassifyRequest): The model representing the
            classify request.

        Returns:
            ClassifyResponse: The model representing the classify
            response.

        """
        grpc_request = ClassifyRequest(
            deployment_id=request.deployment_id,
            inputs=[
                ClassificationInput(
                    affiliate=request_input.affiliate,
                    correlation_id=request_input.correlation_id,
                    encoding=(
                        RequestEncoding.Value(request_input.encoding)
                        if isinstance(request_input.encoding, str)
                        else request_input.encoding
                    ),
                    data=request_input.data,
                )
                for request_input in request.inputs
            ],
        )
        grpc_response = self.stub.Classify(iter([grpc_request]))
        return ClassifyResponse(
            global_error=grpc_response.global_error,
            outputs=[
                ClassificationOutput(
                    correlation_id=output.correlation_id,
                    classifications=[
                        Classification(
                            label=classification.label,
                            weight=classification.weight,
                        )
                        for classification in output.classifications
                    ],
                    error=output.error,
                )
                for output in grpc_response.outputs
            ],
        )

    def list_deployments(self) -> ListDeploymentsResponse:
        """Retrieve a list of all active deployment IDs.

        Returns:
            ListDeploymentsResponse: The model representing the list
            deployments response.

        """
        grpc_response = self.stub.ListDeployments(Empty())
        return ListDeploymentsResponse(
            deployments=[
                Deployment(
                    deployment_id=grpc_response.deployment.deployment_ids,
                    backlog=grpc_response.deployment.backlog,
                )
                for deployment in grpc_response.deployments
            ]
        )
