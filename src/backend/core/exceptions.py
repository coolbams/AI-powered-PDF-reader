

class EmptyCollectionError(Exception):
    """Raised when the ChromaDB collection has no documents embedded."""

class DocumentNotFoundError(Exception):
    """Raised when the requested doc_name has no chunks in the collection."""
