"""Byte Transformation Processing Middleware.

Abstract version of a middleware, this takes an async iterator of bytes and
transforms each entry using some self.transform method.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Generic, TypeVar

TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


class AsyncTransformer(ABC, AsyncIterator[TOutput], Generic[TInput, TOutput]):
    """Base class for image processing middleware."""

    def __init__(self, source: AsyncIterator[TInput]) -> None:
        """Initialize with source iterator."""
        self.source = source

    @abstractmethod
    async def transform(self, data: TInput) -> TOutput:
        """Asynchronously transform a single chunk of input data.

        Args:
            data: The input data to be transformed, typically an ImageData
            object containing image bytes and calculated hashes.

        Returns:
            The transformed output, as defined by the subclass
                implementation.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.

        """
        message = "Subclasses must implement this method"
        raise NotImplementedError(message)

    async def __anext__(self) -> TOutput:
        """Get next transformed data."""
        data = await anext(self.source)
        return await self.transform(data)
