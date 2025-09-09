"""Low-level GRPC client for the ClassifierService."""

from collections.abc import AsyncIterable
from typing import TYPE_CHECKING

from google.protobuf.empty_pb2 import Empty
from grpc import aio

from resolver_athena_client.generated.athena.athena_pb2 import (
    ClassifyRequest,
    ClassifyResponse,
    ListDeploymentsResponse,
)
from resolver_athena_client.generated.athena.athena_pb2_grpc import (
    ClassifierServiceStub,
)

if TYPE_CHECKING:
    from grpc.aio import StreamStreamCall


class ClassifierServiceClient:
    """Low-level gRPC wrapper for the ClassifierService."""

    def __init__(self, channel: aio.Channel) -> None:
        """Initialize the client with a gRPC channel.

        Args:
            channel (aio.Channel): A gRPC channel to communicate with the
            server.

        """
        self.stub = ClassifierServiceStub(channel)

    async def classify(
        self,
        request_iter: AsyncIterable[ClassifyRequest],
        timeout: float | None = None,
    ) -> "StreamStreamCall[ClassifyRequest, ClassifyResponse]":
        """Perform image classification in a deployment-based streaming context.

        Args:
            request_iter (AsyncIterable[ClassifyRequest]): An async
                iterable of classify requests to be streamed to the server.
            timeout (float | None): RPC timeout in seconds. None for no timeout.
                The overall duration for receiving all responses.

        Returns:
            StreamStreamCall[ClassifyRequest, ClassifyResponse]: A gRPC stream
            call object that can be used as an async iterator of responses.

        """
        return self.stub.Classify(
            request_iter,
            timeout=timeout,
            wait_for_ready=True,
        )

    async def list_deployments(self) -> ListDeploymentsResponse:
        """Retrieve a list of all active deployment IDs.

        Returns:
            ListDeploymentsResponse: The model representing the list
            deployments response.

        """
        return await self.stub.ListDeployments(Empty())
