from pathlib import Path

import pytest

from resolver_athena_client.client.models import ImageData
from tests.functional.conftest import StreamingSender
from tests.functional.e2e.testcases.parser import (
    AthenaTestCase,
    load_test_cases_by_env,
)

TEST_CASES = load_test_cases_by_env()

FP_ERROR_TOLERANCE = 1e-4


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.functional
@pytest.mark.e2e
@pytest.mark.parametrize("test_case", TEST_CASES, ids=lambda tc: tc.id)
async def test_e2e_case(
    streaming_sender: StreamingSender,
    test_case: AthenaTestCase,
) -> None:
    """Functional test for ClassifySingle endpoint and API methods.

    This test creates a unique test image for each iteration and classifies it.

    """

    with Path.open(Path(test_case.filepath), "rb") as f:
        image_bytes = f.read()

    image_data = ImageData(image_bytes)

    # Classify with auto-generated correlation ID
    result = await streaming_sender.send(image_data)

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
    actual_output = {k: actual_output[k] for k in test_case.expected_output}

    for label in test_case.expected_output:
        expected = test_case.expected_output[label]
        actual = actual_output[label]
        diff = abs(expected - actual)
        assert diff < FP_ERROR_TOLERANCE, (
            f"Weight for label '{label}' differs by more than "
            f"{FP_ERROR_TOLERANCE}: expected={expected}, actual={actual}, "
            f"diff={diff}"
        )
