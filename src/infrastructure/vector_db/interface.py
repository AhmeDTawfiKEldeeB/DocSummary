from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence, Union


class BaseVectorDB(ABC):
    """Abstract interface for vector database providers (ISP & DIP)."""

    @abstractmethod
    async def init_collection(
        self,
        collection_name: Optional[str] = None,
        vector_size: int = 1536,
        distance: str = "Cosine",
        **kwargs: Any,
    ) -> bool:
        """Initializes or ensures a collection exists in the vector database."""
        pass

    @abstractmethod
    async def upsert(
        self,
        points: Sequence[Any],
        collection_name: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Inserts or updates vector points in the collection."""
        pass

    @abstractmethod
    async def search(
        self,
        query_vector: Sequence[float],
        collection_name: Optional[str] = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> List[Any]:
        """Searches nearest neighbor vectors for the given query vector."""
        pass

    @abstractmethod
    async def delete(
        self,
        point_ids: Sequence[Union[int, str]],
        collection_name: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Deletes vector points by their IDs."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Verifies connectivity to the vector database service."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Closes active client connections."""
        pass
