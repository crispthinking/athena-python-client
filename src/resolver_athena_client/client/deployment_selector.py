"""Deployment selector for the Athena client."""

import logging
from types import TracebackType

import grpc

from resolver_athena_client.generated.athena.models_pb2 import (
    ListDeploymentsResponse,
)
from resolver_athena_client.grpc_wrappers.classifier_service import (
    ClassifierServiceClient,
)


class DeploymentSelector:
    """A controller for selecting deployments from the Athena service.

    This class provides functionality to list available deployments for use
    with the Athena client. It can be used as an async context manager to ensure
    proper cleanup of resources.

    Attributes:
        classifier (ClassifierServiceClient): The classifier service client used
            to communicate with the Athena service.

    """

    channel: grpc.aio.Channel | None = None
    classifier: ClassifierServiceClient

    def __init__(self, channel: grpc.aio.Channel) -> None:
        """Initialize the deployment selector.

        Args:
            channel (grpc.aio.Channel): Channel with which to communicate with
                the Athena service.

        """
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.classifier = ClassifierServiceClient(channel)

    async def list_deployments(self) -> ListDeploymentsResponse:
        """Retrieve a list of all active deployments.

        Returns:
            ListDeploymentsResponse: Response containing the list of
                deployments.

        """
        self.logger.debug("Retrieving list of deployments from server")
        response = await self.classifier.list_deployments()

        if not response.deployments:
            self.logger.error("No deployments available from server")
        else:
            self.logger.debug(
                "Retrieved %d deployments: %s",
                len(response.deployments),
                ", ".join(
                    [
                        deployment.deployment_id
                        for deployment in response.deployments
                    ]
                ),
            )

        return response

    async def __aenter__(self) -> "DeploymentSelector":
        """Enter the async context manager.

        Returns:
            DeploymentSelector: This instance.

        """
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the async context manager.

        Args:
            exc_type: The type of the exception that was raised
            exc_val: The instance of the exception that was raised
            exc_tb: The traceback of the exception that was raised

        """
        if hasattr(self, "channel") and self.channel is not None:
            await self.channel.close()
