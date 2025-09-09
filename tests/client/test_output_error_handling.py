"""Test classification output error handling functionality."""

import pytest

from resolver_athena_client.client.exceptions import ClassificationOutputError
from resolver_athena_client.client.utils import (
    get_output_error_summary,
    get_successful_outputs,
    has_output_errors,
    log_output_errors,
    process_classification_outputs,
)
from resolver_athena_client.generated.athena.models_pb2 import (
    Classification,
    ClassificationError,
    ClassificationOutput,
    ClassifyResponse,
    ErrorCode,
)

# Test constants
EXPECTED_SUCCESS_COUNT = 2
EXPECTED_ERROR_COUNT = 2


def create_successful_output(
    correlation_id: str = "test-123",
) -> ClassificationOutput:
    """Create a successful classification output for testing."""
    output = ClassificationOutput()
    output.correlation_id = correlation_id

    # Add some classifications
    classification1 = Classification()
    classification1.label = "cat"
    classification1.weight = 0.95
    output.classifications.append(classification1)

    classification2 = Classification()
    classification2.label = "animal"
    classification2.weight = 0.87
    output.classifications.append(classification2)

    return output


def create_error_output(
    correlation_id: str = "error-456",
    error_code: ErrorCode.ValueType = ErrorCode.ERROR_CODE_MODEL_ERROR,
    message: str = "Model inference failed",
    details: str = "",
) -> ClassificationOutput:
    """Create a classification output with an error for testing."""
    output = ClassificationOutput()
    output.correlation_id = correlation_id

    # Set the error
    output.error.code = error_code
    output.error.message = message
    if details:
        output.error.details = details

    return output


def create_response_with_mixed_outputs() -> ClassifyResponse:
    """Create a response with both successful and error outputs."""
    response = ClassifyResponse()

    # Add successful outputs
    response.outputs.append(create_successful_output("success-1"))
    response.outputs.append(create_successful_output("success-2"))

    # Add error outputs
    response.outputs.append(
        create_error_output(
            "error-1",
            ErrorCode.ERROR_CODE_IMAGE_TOO_LARGE,
            "Image exceeds size limit",
            "Max size: 10MB",
        )
    )
    response.outputs.append(
        create_error_output(
            "error-2",
            ErrorCode.ERROR_CODE_MODEL_ERROR,
            "Model failed to process image",
        )
    )

    return response


class TestClassificationOutputError:
    """Test the ClassificationOutputError exception."""

    def test_error_creation_with_all_fields(self) -> None:
        """Test creating error with all fields."""
        error = ClassificationError()
        error.code = ErrorCode.ERROR_CODE_IMAGE_TOO_LARGE
        error.message = "Image too large"
        error.details = "Maximum size exceeded"

        exception = ClassificationOutputError("test-123", error)

        assert exception.correlation_id == "test-123"
        assert exception.error_code == ErrorCode.ERROR_CODE_IMAGE_TOO_LARGE
        assert exception.error_message == "Image too large"
        assert exception.error_details == "Maximum size exceeded"
        assert "test-123" in str(exception)
        assert "Image too large" in str(exception)

    def test_error_creation_with_custom_message(self) -> None:
        """Test creating error with custom message."""
        error = ClassificationError()
        error.code = ErrorCode.ERROR_CODE_MODEL_ERROR
        error.message = "Model failed"

        exception = ClassificationOutputError(
            "test-456", error, "Custom error message"
        )

        assert str(exception) == "Custom error message"

    def test_error_creation_with_details(self) -> None:
        """Test error message includes details when present."""
        error = ClassificationError()
        error.code = ErrorCode.ERROR_CODE_MODEL_ERROR
        error.message = "Model failed"
        error.details = "GPU memory exhausted"

        exception = ClassificationOutputError("test-789", error)

        assert "Model failed" in str(exception)
        assert "GPU memory exhausted" in str(exception)


class TestHasOutputErrors:
    """Test the has_output_errors function."""

    def test_response_with_no_errors(self) -> None:
        """Test response with only successful outputs."""
        response = ClassifyResponse()
        response.outputs.append(create_successful_output("test-1"))
        response.outputs.append(create_successful_output("test-2"))

        assert not has_output_errors(response)

    def test_response_with_errors(self) -> None:
        """Test response with error outputs."""
        response = create_response_with_mixed_outputs()
        assert has_output_errors(response)

    def test_empty_response(self) -> None:
        """Test empty response."""
        response = ClassifyResponse()
        assert not has_output_errors(response)

    def test_response_with_empty_error_message(self) -> None:
        """Test output with error object but empty message."""
        response = ClassifyResponse()
        output = ClassificationOutput()
        output.correlation_id = "test-123"
        output.error.code = ErrorCode.ERROR_CODE_MODEL_ERROR
        output.error.message = ""  # Empty message
        response.outputs.append(output)

        assert not has_output_errors(response)


class TestGetSuccessfulOutputs:
    """Test the get_successful_outputs function."""

    def test_mixed_response(self) -> None:
        """Test filtering successful outputs from mixed response."""
        response = create_response_with_mixed_outputs()
        successful = get_successful_outputs(response)

        assert len(successful) == EXPECTED_SUCCESS_COUNT
        assert all(
            not (output.error and output.error.message) for output in successful
        )
        assert successful[0].correlation_id == "success-1"
        assert successful[1].correlation_id == "success-2"

    def test_all_successful_response(self) -> None:
        """Test response with only successful outputs."""
        response = ClassifyResponse()
        response.outputs.append(create_successful_output("test-1"))
        response.outputs.append(create_successful_output("test-2"))

        successful = get_successful_outputs(response)
        assert len(successful) == EXPECTED_SUCCESS_COUNT

    def test_all_error_response(self) -> None:
        """Test response with only error outputs."""
        response = ClassifyResponse()
        response.outputs.append(create_error_output("error-1"))
        response.outputs.append(create_error_output("error-2"))

        successful = get_successful_outputs(response)
        assert len(successful) == 0

    def test_empty_response(self) -> None:
        """Test empty response."""
        response = ClassifyResponse()
        successful = get_successful_outputs(response)
        assert len(successful) == 0


class TestGetOutputErrorSummary:
    """Test the get_output_error_summary function."""

    def test_mixed_response_error_summary(self) -> None:
        """Test error summary for mixed response."""
        response = create_response_with_mixed_outputs()
        summary = get_output_error_summary(response)

        expected_summary = {
            str(ErrorCode.ERROR_CODE_IMAGE_TOO_LARGE): 1,
            str(ErrorCode.ERROR_CODE_MODEL_ERROR): 1,
        }
        assert summary == expected_summary

    def test_no_errors_summary(self) -> None:
        """Test error summary for response with no errors."""
        response = ClassifyResponse()
        response.outputs.append(create_successful_output("test-1"))
        response.outputs.append(create_successful_output("test-2"))

        summary = get_output_error_summary(response)
        assert summary == {}

    def test_multiple_same_errors(self) -> None:
        """Test error summary with multiple errors of same type."""
        response = ClassifyResponse()
        response.outputs.append(
            create_error_output("error-1", ErrorCode.ERROR_CODE_MODEL_ERROR)
        )
        response.outputs.append(
            create_error_output("error-2", ErrorCode.ERROR_CODE_MODEL_ERROR)
        )
        response.outputs.append(
            create_error_output("error-3", ErrorCode.ERROR_CODE_MODEL_ERROR)
        )

        summary = get_output_error_summary(response)
        assert summary == {str(ErrorCode.ERROR_CODE_MODEL_ERROR): 3}


class TestProcessClassificationOutputs:
    """Test the process_classification_outputs function."""

    def test_process_mixed_outputs_raise_false(self) -> None:
        """Test processing mixed outputs without raising exceptions."""
        response = create_response_with_mixed_outputs()

        successful = process_classification_outputs(
            response, raise_on_error=False, log_errors=False
        )

        assert len(successful) == EXPECTED_SUCCESS_COUNT
        assert successful[0].correlation_id == "success-1"
        assert successful[1].correlation_id == "success-2"

    def test_process_mixed_outputs_raise_true(self) -> None:
        """Test processing mixed outputs with raising exceptions."""
        response = create_response_with_mixed_outputs()

        with pytest.raises(ClassificationOutputError) as exc_info:
            process_classification_outputs(response, raise_on_error=True)

        assert exc_info.value.correlation_id == "error-1"
        assert exc_info.value.error_code == ErrorCode.ERROR_CODE_IMAGE_TOO_LARGE

    def test_process_all_successful_outputs(self) -> None:
        """Test processing response with only successful outputs."""
        response = ClassifyResponse()
        response.outputs.append(create_successful_output("test-1"))
        response.outputs.append(create_successful_output("test-2"))

        successful = process_classification_outputs(
            response, raise_on_error=True
        )
        assert len(successful) == EXPECTED_SUCCESS_COUNT

    def test_process_all_error_outputs_raise_false(self) -> None:
        """Test processing response with only error outputs, no raising."""
        response = ClassifyResponse()
        response.outputs.append(create_error_output("error-1"))
        response.outputs.append(create_error_output("error-2"))

        successful = process_classification_outputs(
            response, raise_on_error=False, log_errors=False
        )
        assert len(successful) == 0

    def test_process_all_error_outputs_raise_true(self) -> None:
        """Test processing response with only error outputs, with raising."""
        response = ClassifyResponse()
        response.outputs.append(create_error_output("error-1"))

        with pytest.raises(ClassificationOutputError):
            process_classification_outputs(response, raise_on_error=True)

    def test_process_empty_response(self) -> None:
        """Test processing empty response."""
        response = ClassifyResponse()

        successful = process_classification_outputs(
            response, raise_on_error=True
        )
        assert len(successful) == 0


class TestLogOutputErrors:
    """Test the log_output_errors function."""

    def test_log_errors_in_mixed_response(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test logging errors in mixed response."""
        response = create_response_with_mixed_outputs()

        with caplog.at_level("ERROR"):
            log_output_errors(response)

        # Should have logged 2 errors
        error_records = [
            record for record in caplog.records if record.levelname == "ERROR"
        ]
        assert len(error_records) == EXPECTED_ERROR_COUNT

        # Check error messages contain correlation IDs
        assert "error-1" in error_records[0].message
        assert "error-2" in error_records[1].message

    def test_log_no_errors(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test logging when there are no errors."""
        response = ClassifyResponse()
        response.outputs.append(create_successful_output("test-1"))

        with caplog.at_level("ERROR"):
            log_output_errors(response)

        error_records = [
            record for record in caplog.records if record.levelname == "ERROR"
        ]
        assert len(error_records) == 0

    def test_log_error_with_details(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test logging error with details."""
        response = ClassifyResponse()
        response.outputs.append(
            create_error_output(
                "test-123",
                ErrorCode.ERROR_CODE_IMAGE_TOO_LARGE,
                "Image too large",
                "Max size: 10MB",
            )
        )

        with caplog.at_level("DEBUG"):
            log_output_errors(response)

        # Check that details are logged at DEBUG level
        debug_records = [
            record for record in caplog.records if record.levelname == "DEBUG"
        ]
        assert len(debug_records) == 1
        assert "Max size: 10MB" in debug_records[0].message
