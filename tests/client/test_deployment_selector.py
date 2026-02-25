"""Tests for deployment selector."""

from unittest import mock

import pytest
from grpc import aio
from resolver_athena_client.generated.athena.models_pb2 import (
    Deployment,
    ListDeploymentsResponse,
)

from resolver_athena_client.client.deployment_selector import DeploymentSelector
from resolver_athena_client.grpc_wrappers.classifier_service import (
    ClassifierServiceClient,
)


@pytest.fixture
def mock_channel() -> mock.Mock:
    """Fixture providing a mock gRPC channel."""
    return mock.Mock(spec=aio.Channel)


@pytest.fixture
def mock_classifier_client() -> mock.Mock:
    """Fixture providing a mock classifier client."""
    return mock.Mock(spec=ClassifierServiceClient)


@pytest.mark.asyncio
async def test_list_deployments_success(mock_channel: mock.Mock) -> None:
    """Test successful deployment listing."""
    # Create test data
    test_deployments = [
        Deployment(deployment_id="test-deployment-1"),
        Deployment(deployment_id="test-deployment-2"),
    ]
    expected_response = ListDeploymentsResponse(deployments=test_deployments)

    # Setup mock
    with mock.patch(
        "resolver_athena_client.client.deployment_selector.ClassifierServiceClient"
    ) as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.list_deployments = mock.AsyncMock(
            return_value=expected_response
        )

        # Create selector and list deployments
        selector = DeploymentSelector(mock_channel)
        response = await selector.list_deployments()

        # Define expected count
        expected_deployment_count = 2

        # Verify response
        assert response == expected_response
        assert len(response.deployments) == expected_deployment_count
        assert response.deployments[0].deployment_id == "test-deployment-1"
        assert response.deployments[1].deployment_id == "test-deployment-2"

        # Verify client interaction
        mock_client_cls.assert_called_once_with(mock_channel)
        mock_client.list_deployments.assert_called_once()


@pytest.mark.asyncio
async def test_list_deployments_empty(mock_channel: mock.Mock) -> None:
    """Test deployment listing when no deployments are available."""
    # Create empty response
    empty_response = ListDeploymentsResponse(deployments=[])

    # Setup mock
    with mock.patch(
        "resolver_athena_client.client.deployment_selector.ClassifierServiceClient"
    ) as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.list_deployments = mock.AsyncMock(
            return_value=empty_response
        )

        # Create selector and list deployments
        selector = DeploymentSelector(mock_channel)
        response = await selector.list_deployments()

        # Verify response
        assert response == empty_response
        assert len(response.deployments) == 0

        # Verify client interaction
        mock_client_cls.assert_called_once_with(mock_channel)
        mock_client.list_deployments.assert_called_once()


@pytest.mark.asyncio
async def test_list_deployments_client_error(mock_channel: mock.Mock) -> None:
    """Test deployment listing when client raises an error."""
    # Setup mock to raise error
    with mock.patch(
        "resolver_athena_client.client.deployment_selector.ClassifierServiceClient"
    ) as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.list_deployments = mock.AsyncMock(
            side_effect=RuntimeError("Test error")
        )

        # Create selector
        selector = DeploymentSelector(mock_channel)

        # Verify error is propagated
        with pytest.raises(RuntimeError, match="Test error"):
            _ = await selector.list_deployments()

        # Verify client interaction
        mock_client_cls.assert_called_once_with(mock_channel)
        mock_client.list_deployments.assert_called_once()
