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
from tests.utils.mock_stream_call import MockStreamCall


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

    # Create stream call mock that will return our response
    mock_stream = MockStreamCall([mock_response])

    # Replace stub's Classify method with our mock
    client.stub.Classify = mock_stream

    # Get stream from classify call
    stream = await client.classify(mock_request_iter)

    # Collect responses from stream
    responses = [response async for response in stream]

    # Verify response
    assert len(responses) == 1
    assert isinstance(responses[0], ClassifyResponse)
    assert mock_stream.call_count == 1
