"""Provides correlation ID generation functionality."""

from __future__ import annotations

import abc
import hashlib
from typing import override

from resolver_athena_client.client.consts import MAX_DEPLOYMENT_ID_LENGTH

__all__ = ["CorrelationProvider", "HashCorrelationProvider"]


class CorrelationProvider(abc.ABC):
    """Abstract base class defining the contract for correlation ID generation.

    This class serves as an interface for different strategies of generating
    correlation IDs. Implementations can use various methods such as hashing,
    UUIDs, or other approaches to generate unique identifiers.
    """

    @abc.abstractmethod
    def get_correlation_id(self, input_data: bytes | str | bytearray) -> str:
        """Generate a correlation ID for the given input data.

        Args:
        ----
            input_data: Data to use as the basis for correlation ID generation.
                The type and structure of this data depends on the specific
                implementation.

        Returns:
        -------
            A string containing the generated correlation ID.

        Raises:
        ------
            ValueError: If the input data is not in a format supported by
                the implementation.

        """
        raise NotImplementedError


class HashCorrelationProvider(CorrelationProvider):
    """Generates correlation IDs by hashing the input data.

    This implementation uses SHA-256 to generate a deterministic hash of the
    input data's bytes, which serves as the correlation ID.
    """

    @override
    def get_correlation_id(self, input_data: bytes | str | bytearray) -> str:
        """Generate a correlation ID by hashing the input data.

        The input data is converted to bytes using the following rules:
        - If input is bytes, use directly
        - If input is str, encode as UTF-8
        - Otherwise, convert to string and encode as UTF-8

        Args:
        ----
            input_data: Data to hash for correlation ID generation.

        Returns:
        -------
            A hex string of the SHA-256 hash of the input data.

        Raises:
        ------
            ValueError: If the input data cannot be converted to bytes.

        """
        try:
            if isinstance(input_data, bytes):
                data_bytes = input_data
            elif isinstance(input_data, str):
                data_bytes = input_data.encode("utf-8")
            else:
                data_bytes = str(input_data).encode("utf-8")

            return hashlib.sha256(data_bytes).hexdigest()[
                :MAX_DEPLOYMENT_ID_LENGTH
            ]
        except Exception as e:
            error_msg = f"Failed to generate correlation ID from input: {e}"
            raise ValueError(error_msg) from e
