import chromadb
from .embeddings import EmbeddingModel, CHROMA_DB_PATH
from .exceptions import EmptyCollectionError, DocumentNotFoundError

embed = EmbeddingModel()

class Retrieval:
    """Connects to ChromaDB and performs semantic search over embedded PDF chunks."""

    def __init__(self):
        """Initialises the ChromaDB client and opens the shared embeddings collection."""
        self.client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
        self.collection = self.client.get_or_create_collection("my_embedded_pdfs")

    def search(self, query: str, top_k: int = 5, doc_name: str | None = None) -> list[dict]:
        """Embeds the query and returns the top-k most relevant chunks from the vector store.
        If doc_name is provided, filters results to that document only."""

        # Guard: collection must have at least one document before querying
        if self.collection.count() == 0:
            raise EmptyCollectionError("No documents have been uploaded yet.")

        query_embedding = embed.embed_query(query)

        where_filter = {"doc_name": doc_name} if doc_name else None

        # Guard: if filtering by doc_name, make sure it actually exists
        if doc_name:
            doc_check = self.collection.get(where={"doc_name": doc_name}, limit=1)
            if not doc_check["ids"]:
                raise DocumentNotFoundError(f"Document '{doc_name}' not found in the collection.")

        # Clamp n_results to the actual collection size to avoid a ChromaDB crash
        n = min(top_k, self.collection.count())

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n,
            where=where_filter,
        )

        chunks = []
        for i in range(len(results["ids"][0])):
            chunks.append({
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "id": results["ids"][0][i],
                "distance": results["distances"][0][i],
            })

        return chunks
