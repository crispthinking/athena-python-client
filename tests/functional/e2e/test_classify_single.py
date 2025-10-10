from pathlib import Path

import pytest

from resolver_athena_client.client.athena_client import AthenaClient
from resolver_athena_client.client.athena_options import AthenaOptions
from resolver_athena_client.client.channel import (
    CredentialHelper,
    create_channel_with_credentials,
)
from resolver_athena_client.client.models import ImageData
from tests.functional.e2e.testcases.parser import (
    AthenaTestCase,
    load_test_cases,
)

TEST_CASES = load_test_cases("benign_model")

FP_ERROR_TOLERANCE = 1e-4


@pytest.mark.asyncio
@pytest.mark.functional
@pytest.mark.parametrize("test_case", TEST_CASES, ids=lambda tc: tc.id)
async def test_classify_single(
    athena_options: AthenaOptions,
    credential_helper: CredentialHelper,
    test_case: AthenaTestCase,
) -> None:
    """Functional test for ClassifySingle endpoint and API methods.

    This test creates a unique test image for each iteration and classifies it.
    The test runs multiple iterations to ensure consistent behavior.
    """

    # Create gRPC channel with credentials
    channel = await create_channel_with_credentials(
        athena_options.host, credential_helper
    )
    with Path.open(Path(test_case.filepath), "rb") as f:
        image_bytes = f.read()

    async with AthenaClient(channel, athena_options) as client:

        image_data = ImageData(image_bytes)

        # Classify with auto-generated correlation ID
        result = await client.classify_single(image_data)

        if result.error.code:
            msg = f"Image Result Error: {result.error.message}"
            pytest.fail(msg)

        actual_output = {c.label: c.weight for c in result.classifications}
        assert set(test_case.expected_output.keys()).issubset(
            set(actual_output.keys())
        ), (
            "Expected output to contain labels: ",
            f"{test_case.expected_output.keys() - actual_output.keys()}",
        )

        max_diff = max(
            abs(test_case.expected_output[label] - actual_output[label])
            for label in test_case.expected_output
        )
        assert max_diff < FP_ERROR_TOLERANCE, (
            "Output weights differ from expected by more than",
            f" {FP_ERROR_TOLERANCE}: ",
            f"expected={test_case.expected_output}, actual={actual_output}",
        )
