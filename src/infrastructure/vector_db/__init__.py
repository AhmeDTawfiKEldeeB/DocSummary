try:
    from src.infrastructure.vector_db.factory import registry
    from src.infrastructure.vector_db.interface import BaseVectorDB
    from src.infrastructure.vector_db.providers.qdrant import (
        QdrantProvider,
        QdrantVectorDB,
        get_qdrant_client,
        init_qdrant,
    )
except ModuleNotFoundError:
    from infrastructure.vector_db.factory import registry
    from infrastructure.vector_db.interface import BaseVectorDB
    from infrastructure.vector_db.providers.qdrant import (
        QdrantProvider,
        QdrantVectorDB,
        get_qdrant_client,
        init_qdrant,
    )


def get_vector_db(name: str = "qdrant") -> BaseVectorDB:
    """Retrieves a pre-initialized vector database provider instance by name."""
    return registry.get_provider(name)


__all__ = [
    "get_vector_db",
    "BaseVectorDB",
    "QdrantProvider",
    "QdrantVectorDB",
    "init_qdrant",
    "get_qdrant_client",
]
