from unittest.mock import AsyncMock, MagicMock

import pytest
from google.protobuf.empty_pb2 import Empty

from athena_client.generated.athena.athena_pb2 import (
    ClassifyResponse,
    ListDeploymentsResponse,
)
from athena_client.grpc_wrappers.classifier_service import (
    ClassifierServiceClient,
)
from tests.utils.mock_async_iterator import MockAsyncIterator


@pytest.fixture
def client() -> ClassifierServiceClient:
    return ClassifierServiceClient(channel=MagicMock())


@pytest.mark.asyncio
async def test_list_deployments(client: ClassifierServiceClient) -> None:
    expected_response = ListDeploymentsResponse()
    client.stub.ListDeployments = AsyncMock(return_value=expected_response)

    response = await client.list_deployments()

    client.stub.ListDeployments.assert_awaited_once_with(Empty())
    assert response == expected_response


@pytest.mark.asyncio
async def test_classify(client: ClassifierServiceClient) -> None:
    mock_request_iter = AsyncMock()

    mock_response = ClassifyResponse()
    client.stub.Classify = lambda _: MockAsyncIterator([mock_response])

    responses = [
        response async for response in client.classify(mock_request_iter)
    ]

    assert len(responses) == 1
    assert isinstance(responses[0], ClassifyResponse)
