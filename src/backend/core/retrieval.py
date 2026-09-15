import chromadb
from .embeddings import EmbeddingModel, CHROMA_DB_PATH

embed = EmbeddingModel()

class Retrieval:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
        self.collection = self.client.get_or_create_collection("my_embedded_pdfs")

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        query_embedding = embed.embed_query(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
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
