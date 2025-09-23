from collections.abc import AsyncIterable
from typing import Generic, Self, TypeVar

T = TypeVar("T")


class MockAsyncIterator(Generic[T]):
    def __init__(self, items: list[T]) -> None:
        self._items: list[T] = items.copy()
        self.call_count: int = 0
        self._timeout: float | None = None

    async def __call__(
        self,
        _: AsyncIterable[bytes],
        *,
        timeout: float | None = None,
    ) -> "MockAsyncIterator[T]":
        self.call_count += 1
        # Store timeout for potential use in testing
        self._timeout = timeout
        return self

    def __aiter__(self) -> Self:
        return self

    async def __anext__(self) -> T:
        if not self._items:
            raise StopAsyncIteration
        return self._items.pop(0)
