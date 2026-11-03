from typing import Optional
from src.infrastructure.storage.interface import BaseFileStorage
from src.infrastructure.storage.local import LocalFileStorage

_storage_instance: Optional[BaseFileStorage] = None


def get_storage() -> BaseFileStorage:
    """Returns the singleton storage provider instance."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = LocalFileStorage()
    return _storage_instance


__all__ = [
    "BaseFileStorage",
    "LocalFileStorage",
    "get_storage",
]
