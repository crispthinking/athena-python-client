"""Byte Transformation Processing Middleware.

Abstract version of a middleware, this takes an async iterator of bytes and
transforms each entry using some self.transform method.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import TypeVar

T = TypeVar("T")


class AsyncTransformer(ABC, AsyncIterator[T]):
    """Base class for image processing middleware."""

    def __init__(self, source: AsyncIterator[bytes]) -> None:
        """Initialize with source iterator."""
        self.source = source

    @abstractmethod
    async def transform(self, data: bytes) -> T:
        """Transform the image bytes."""
        message = "Subclasses must implement this method"
        raise NotImplementedError(message)

    async def __anext__(self) -> T:
        """Get next transformed bytes."""
        data = await anext(self.source)
        return await self.transform(data)
