"""Low-level GRPC client for the ClassifierService."""

from collections.abc import AsyncIterable

import grpc
import grpc.aio
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

    def __init__(self, channel: grpc.aio.Channel) -> None:
        """Initialize the client with a gRPC channel.

        Args:
            channel (grpc.aio.Channel): A gRPC channel to communicate with the
            server.

        """
        self.stub = ClassifierServiceStub(channel)

    async def classify(
        self, request_iter: AsyncIterable[ClassifyRequest]
    ) -> AsyncIterable[ClassifyResponse]:
        """Perform image classification in a deployment-based streaming context.

        Args:
            request_iter (AsyncIterable[ClassifyRequest]): An async
            iterable of classify requests to be streamed to the server.

        Yields:
            AsyncIterable[ClassifyResponse]: A generator yielding classify
            responses from the server.

        """
        async for grpc_request in request_iter:
            request = ClassifyRequest(
                deployment_id=grpc_request.deployment_id,
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
                    for request_input in grpc_request.inputs
                ],
            )

            async for grpc_response in self.stub.Classify(iter([request])):
                yield ClassifyResponse(
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
                    deployment_id=deployment.deployment_id,
                    backlog=deployment.backlog,
                )
                for deployment in grpc_response.deployments
            ]
        )
