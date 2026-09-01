from collections.abc import Callable
from threading import Lock
from typing import Any


class InMemoryCache:
    """Cache de proceso simple, invalidado explicitamente en escritura (sin TTL)."""

    def __init__(self):
        self._store: dict[str, Any] = {}
        self._lock = Lock()

    def get_or_set(self, key: str, loader: Callable[[], Any]) -> Any:
        with self._lock:
            if key in self._store:
                return self._store[key]
            value = loader()
            self._store[key] = value
            return value

    def invalidate_all(self) -> None:
        with self._lock:
            self._store.clear()


cache = InMemoryCache()
