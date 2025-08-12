"""Low-level GRPC client for the ClassifierService."""

from collections.abc import AsyncIterable

import grpc
import grpc.aio
from google.protobuf.empty_pb2 import Empty

from athena_client.generated.athena.athena_pb2 import (
    ClassifyRequest,
    ClassifyResponse,
    ListDeploymentsResponse,
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
        async for grpc_response in self.stub.Classify(request_iter):
            yield grpc_response

    async def list_deployments(self) -> ListDeploymentsResponse:
        """Retrieve a list of all active deployment IDs.

        Returns:
            ListDeploymentsResponse: The model representing the list
            deployments response.

        """
        return await self.stub.ListDeployments(Empty())
