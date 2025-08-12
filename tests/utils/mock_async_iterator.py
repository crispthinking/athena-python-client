from typing import Generic, Self, TypeVar

T = TypeVar("T")


class MockAsyncIterator(Generic[T]):
    def __init__(self, items: list[T]) -> None:
        self._items = items

    def __aiter__(self) -> Self:
        return self

    async def __anext__(self) -> T:
        if not self._items:
            raise StopAsyncIteration
        return self._items.pop(0)
