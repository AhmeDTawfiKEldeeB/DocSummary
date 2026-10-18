from typing import Dict, Optional

try:
    from src.config.settings import Settings, get_settings
    from src.infrastructure.vector_db.interface import BaseVectorDB
    from src.infrastructure.vector_db.providers.qdrant import QdrantProvider
except ModuleNotFoundError:
    from config.settings import Settings, get_settings
    from infrastructure.vector_db.interface import BaseVectorDB
    from infrastructure.vector_db.providers.qdrant import QdrantProvider


class VectorDBRegistry:
    """Central registry and factory for vector database providers."""

    def __init__(self) -> None:
        self._providers: Dict[str, BaseVectorDB] = {}

    def register_provider(self, key: str, provider: BaseVectorDB) -> None:
        self._providers[key] = provider

    def get_provider(self, key: str = "qdrant") -> BaseVectorDB:
        if key not in self._providers:
            raise KeyError(
                f"Vector DB Provider '{key}' is not initialized. Available: {list(self._providers.keys())}"
            )
        return self._providers[key]


# Global Registry Instance
registry = VectorDBRegistry()


def initialize_vector_db(cfg: Optional[Settings] = None) -> None:
    """Reads configuration settings and registers vector database providers."""
    config = cfg or get_settings()

    # Register Qdrant provider
    registry.register_provider(
        "qdrant",
        QdrantProvider(
            url=config.qdrant_url,
            api_key=config.qdrant_api_key,
            collection_name=config.qdrant_collection_name,
        ),
    )


# Trigger initialization upon module import
initialize_vector_db()
