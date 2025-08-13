"""Deployment selector for the Athena client."""

import logging

import grpc

from athena_client.generated.athena.athena_pb2 import ListDeploymentsResponse
from athena_client.grpc_wrappers.classifier_service import (
    ClassifierServiceClient,
)


class DeploymentSelector:
    """A controller for selecting deployments from the Athena service.

    This class provides functionality to list available deployments for use
    with the Athena client.

    Attributes:
        classifier (ClassifierServiceClient): The classifier service client used
            to communicate with the Athena service.

    """

    def __init__(self, channel: grpc.aio.Channel) -> None:
        """Initialize the deployment selector.

        Args:
            channel (grpc.aio.Channel): Channel with which to communicate with
                the Athena service.

        """
        self.logger = logging.getLogger(__name__)
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
