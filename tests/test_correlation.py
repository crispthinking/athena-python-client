"""Tests for correlation ID generation."""

from typing import cast, override

import pytest

from resolver_athena_client.client.correlation import HashCorrelationProvider


def test_hash_correlation_provider_with_bytes() -> None:
    """Test correlation ID generation with bytes input."""
    provider = HashCorrelationProvider()
    test_input = b"test data"
    correlation_id = provider.get_correlation_id(test_input)

    # SHA-256 of b"test data"
    expected = "916f0027a575074ce72a331777c3478d6513f786a591bd892da1a577bf2335f"
    assert correlation_id == expected


def test_hash_correlation_provider_with_string() -> None:
    """Test correlation ID generation with string input."""
    provider = HashCorrelationProvider()
    test_input = "test data"
    correlation_id = provider.get_correlation_id(test_input)

    # SHA-256 of "test data" encoded as UTF-8
    expected = "916f0027a575074ce72a331777c3478d6513f786a591bd892da1a577bf2335f"
    assert correlation_id == expected


def test_hash_correlation_provider_with_bytearray() -> None:
    """Test correlation ID generation with bytearray input."""
    provider = HashCorrelationProvider()
    test_input = bytearray(b"test data")
    correlation_id = provider.get_correlation_id(test_input)

    # Convert bytearray to string before hashing
    # This matches provider's behavior
    expected = "77d31b8539e943c4a1b3e54b971b979e6b666f9d354d0af433e22c0e5d0e90b"
    assert correlation_id == expected


def test_hash_correlation_provider_with_invalid_input() -> None:
    """Test correlation ID generation with invalid input.

    Tests handling of input that cannot be converted to bytes.
    """
    provider = HashCorrelationProvider()

    # Create an object that raises an exception when converted to string
    class BadStr:
        @override
        def __str__(self) -> str:
            error_msg = "Cannot convert to string"
            raise ValueError(error_msg)

    string = BadStr()

    # do bad stuff to get around type issues
    string = cast("object", string)
    string = cast("str", string)

    with pytest.raises(
        ValueError, match="Failed to generate correlation ID from input"
    ):
        _ = provider.get_correlation_id(string)


def test_hash_correlation_provider_consistency() -> None:
    """Test that the same input always generates the same correlation ID."""
    provider = HashCorrelationProvider()
    test_input = "test data"

    id1 = provider.get_correlation_id(test_input)
    id2 = provider.get_correlation_id(test_input)

    assert id1 == id2


def test_hash_correlation_provider_uniqueness() -> None:
    """Test that different inputs generate different correlation IDs."""
    provider = HashCorrelationProvider()

    id1 = provider.get_correlation_id("test1")
    id2 = provider.get_correlation_id("test2")

    assert id1 != id2
