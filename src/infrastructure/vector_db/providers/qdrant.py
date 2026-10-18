"""
Qdrant Vector Database Provider and Initialization Adapter.
"""

from typing import Any, Dict, List, Optional, Sequence, Union
from qdrant_client import AsyncQdrantClient, QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

try:
    from src.config.settings import settings
    from src.infrastructure.vector_db.interface import BaseVectorDB
except ModuleNotFoundError:
    from config.settings import settings
    from infrastructure.vector_db.interface import BaseVectorDB


DISTANCE_MAPPING: Dict[str, Distance] = {
    "cosine": Distance.COSINE,
    "euclid": Distance.EUCLID,
    "euclidean": Distance.EUCLID,
    "dot": Distance.DOT,
    "manhattan": Distance.MANHATTAN,
}


def resolve_distance(distance: Union[Distance, str]) -> Distance:
    """Resolves distance string or enum to Qdrant Distance enum."""
    if isinstance(distance, Distance):
        return distance
    resolved = DISTANCE_MAPPING.get(distance.lower())
    if resolved is None:
        raise ValueError(
            f"Unsupported distance metric '{distance}'. Supported: {list(DISTANCE_MAPPING.keys())}"
        )
    return resolved


class QdrantProvider(BaseVectorDB):
    """Adapter and client manager for Qdrant Vector Database."""

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        collection_name: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        grpc_port: Optional[int] = None,
        prefer_grpc: bool = False,
        location: Optional[str] = None,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ):
        self.collection_name = (
            collection_name or getattr(settings, "qdrant_collection_name", "documents")
        )
        self.api_key = api_key or getattr(settings, "qdrant_api_key", None)
        self.location = location
        self.host = host
        self.port = port
        self.grpc_port = grpc_port
        self.prefer_grpc = prefer_grpc
        self.timeout = timeout

        if not self.location and not (self.host and self.port):
            self.url = (
                url or getattr(settings, "qdrant_url", None) or "http://localhost:6333"
            )
        else:
            self.url = url

        client_kwargs: Dict[str, Any] = dict(kwargs)
        if self.location:
            client_kwargs["location"] = self.location
        elif self.host and self.port:
            client_kwargs["host"] = self.host
            client_kwargs["port"] = self.port
            if self.grpc_port:
                client_kwargs["grpc_port"] = self.grpc_port
            client_kwargs["prefer_grpc"] = self.prefer_grpc
        elif self.url:
            client_kwargs["url"] = self.url
            if self.prefer_grpc:
                client_kwargs["prefer_grpc"] = self.prefer_grpc

        if self.api_key:
            client_kwargs["api_key"] = self.api_key
        if self.timeout is not None:
            client_kwargs["timeout"] = self.timeout

        self._client_kwargs = client_kwargs
        self.async_client: AsyncQdrantClient = AsyncQdrantClient(**client_kwargs)
        self._sync_client: Optional[QdrantClient] = None

    @property
    def client(self) -> QdrantClient:
        """Returns a synchronous QdrantClient instance (lazy initialized)."""
        if self._sync_client is None:
            self._sync_client = QdrantClient(**self._client_kwargs)
        return self._sync_client

    async def init_collection(
        self,
        collection_name: Optional[str] = None,
        vector_size: int = 1536,
        distance: Union[Distance, str] = Distance.COSINE,
        on_disk_payload: bool = True,
        **kwargs: Any,
    ) -> bool:
        """
        Initializes or ensures a collection exists in Qdrant with the specified vector configuration.
        Returns True if newly created, False if it already existed.
        """
        target_collection = collection_name or self.collection_name
        exists = await self.async_client.collection_exists(target_collection)
        if exists:
            return False

        metric = resolve_distance(distance)
        vectors_config = VectorParams(
            size=vector_size,
            distance=metric,
            **kwargs.pop("vectors_config_kwargs", {}),
        )
        await self.async_client.create_collection(
            collection_name=target_collection,
            vectors_config=vectors_config,
            on_disk_payload=on_disk_payload,
            **kwargs,
        )
        return True

    def init_collection_sync(
        self,
        collection_name: Optional[str] = None,
        vector_size: int = 1536,
        distance: Union[Distance, str] = Distance.COSINE,
        on_disk_payload: bool = True,
        **kwargs: Any,
    ) -> bool:
        """
        Synchronously initializes or ensures a collection exists in Qdrant.
        Returns True if newly created, False if it already existed.
        """
        target_collection = collection_name or self.collection_name
        exists = self.client.collection_exists(target_collection)
        if exists:
            return False

        metric = resolve_distance(distance)
        vectors_config = VectorParams(
            size=vector_size,
            distance=metric,
            **kwargs.pop("vectors_config_kwargs", {}),
        )
        self.client.create_collection(
            collection_name=target_collection,
            vectors_config=vectors_config,
            on_disk_payload=on_disk_payload,
            **kwargs,
        )
        return True

    async def upsert(
        self,
        points: Sequence[Union[PointStruct, Dict[str, Any]]],
        collection_name: Optional[str] = None,
        wait: bool = True,
        **kwargs: Any,
    ) -> Any:
        """Inserts or updates points into the specified Qdrant collection."""
        target_collection = collection_name or self.collection_name
        formatted_points: List[PointStruct] = []
        for p in points:
            if isinstance(p, PointStruct):
                formatted_points.append(p)
            elif isinstance(p, dict):
                formatted_points.append(
                    PointStruct(
                        id=p["id"],
                        vector=p["vector"],
                        payload=p.get("payload", {}),
                    )
                )
            else:
                formatted_points.append(p)

        return await self.async_client.upsert(
            collection_name=target_collection,
            points=formatted_points,
            wait=wait,
            **kwargs,
        )

    async def search(
        self,
        query_vector: Sequence[float],
        collection_name: Optional[str] = None,
        limit: int = 10,
        query_filter: Optional[Any] = None,
        with_payload: bool = True,
        with_vectors: bool = False,
        **kwargs: Any,
    ) -> List[Any]:
        """
        Searches nearest neighbor vectors for the given query vector.
        Uses query_points under the hood and returns the scored points list.
        """
        target_collection = collection_name or self.collection_name
        response = await self.async_client.query_points(
            collection_name=target_collection,
            query=query_vector,
            limit=limit,
            query_filter=query_filter,
            with_payload=with_payload,
            with_vectors=with_vectors,
            **kwargs,
        )
        return response.points

    async def retrieve(
        self,
        point_ids: Sequence[Union[int, str]],
        collection_name: Optional[str] = None,
        with_payload: bool = True,
        with_vectors: bool = False,
        **kwargs: Any,
    ) -> List[Any]:
        """Retrieves points by their IDs from the specified Qdrant collection."""
        target_collection = collection_name or self.collection_name
        return await self.async_client.retrieve(
            collection_name=target_collection,
            ids=point_ids,
            with_payload=with_payload,
            with_vectors=with_vectors,
            **kwargs,
        )

    async def delete(
        self,
        point_ids: Sequence[Union[int, str]],
        collection_name: Optional[str] = None,
        wait: bool = True,
        **kwargs: Any,
    ) -> Any:
        """Deletes vector points by ID from the specified Qdrant collection."""
        target_collection = collection_name or self.collection_name
        return await self.async_client.delete(
            collection_name=target_collection,
            points_selector=point_ids,
            wait=wait,
            **kwargs,
        )

    async def delete_collection(
        self, collection_name: Optional[str] = None, **kwargs: Any
    ) -> bool:
        """Deletes an entire collection from Qdrant."""
        target_collection = collection_name or self.collection_name
        return await self.async_client.delete_collection(
            collection_name=target_collection, **kwargs
        )

    async def health_check(self) -> bool:
        """Verifies connectivity to Qdrant asynchronously."""
        try:
            await self.async_client.get_collections()
            return True
        except Exception:
            return False

    def health_check_sync(self) -> bool:
        """Verifies connectivity to Qdrant synchronously."""
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Closes active Qdrant client connections."""
        await self.async_client.close()
        if self._sync_client is not None:
            self._sync_client.close()


# Aliases for naming convenience
QdrantVectorDB = QdrantProvider


def init_qdrant(
    url: Optional[str] = None,
    api_key: Optional[str] = None,
    collection_name: Optional[str] = None,
    **kwargs: Any,
) -> QdrantProvider:
    """Helper function to initialize and return a QdrantProvider instance."""
    return QdrantProvider(
        url=url,
        api_key=api_key,
        collection_name=collection_name,
        **kwargs,
    )


def get_qdrant_client(
    url: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs: Any,
) -> AsyncQdrantClient:
    """Helper function to initialize and return an AsyncQdrantClient directly."""
    provider = QdrantProvider(url=url, api_key=api_key, **kwargs)
    return provider.async_client


__all__ = [
    "QdrantProvider",
    "QdrantVectorDB",
    "init_qdrant",
    "get_qdrant_client",
    "resolve_distance",
]
