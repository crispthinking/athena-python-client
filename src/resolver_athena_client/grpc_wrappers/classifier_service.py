"""Low-level GRPC client for the ClassifierService."""
# pyright: reportUnknownMemberType = false
# pyright: reportUnknownVariableType = false
# No GRPC typehinting tracked here: https://github.com/grpc/grpc/issues/29041

from collections.abc import AsyncIterable
from typing import TYPE_CHECKING, final

from google.protobuf.empty_pb2 import Empty
from grpc import aio

from resolver_athena_client.generated.athena.athena_pb2_grpc import (
    ClassifierServiceStub,
)
from resolver_athena_client.generated.athena.models_pb2 import (
    ClassificationInput,
    ClassificationOutput,
    ClassifyRequest,
    ClassifyResponse,
    ListDeploymentsResponse,
)

if TYPE_CHECKING:
    from grpc.aio import StreamStreamCall


@final
class ClassifierServiceClient:
    """Low-level gRPC wrapper for the ClassifierService."""

    def __init__(self, channel: aio.Channel) -> None:
        """Initialize the client with a gRPC channel.

        Args:
        ----
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
        ----
            request_iter (AsyncIterable[ClassifyRequest]): An async
                iterable of classify requests to be streamed to the server.
            timeout (float | None): RPC timeout in seconds. None for no timeout.
                The overall duration for receiving all responses.

        Returns:
        -------
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

        Returns
        -------
            ListDeploymentsResponse: The model representing the list
            deployments response.

        """
        return await self.stub.ListDeployments(Empty())

    async def classify_single(
        self,
        request: ClassificationInput,
        timeout: float | None = None,
    ) -> ClassificationOutput:
        """Classify a single image synchronously without deployment context.

        Args:
        ----
            request (ClassificationInput): The classification input containing
                the image data and metadata to be classified.
            timeout (float | None): RPC timeout in seconds. None for no timeout.

        Returns:
        -------
            ClassificationOutput: The classification result containing either
            classifications or error information.

        """
        return await self.stub.ClassifySingle(
            request,
            timeout=timeout,
            wait_for_ready=True,
        )
