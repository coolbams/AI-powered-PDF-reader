import os
import json
import chromadb
from pathlib import Path
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer


load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent

EMBEDDINGS_MODEL_PATH = BASE_DIR / "Embedding_Model"
EMBEDDINGS_MODEL_PATH.mkdir(parents=True, exist_ok=True)

CHROMA_DB_PATH = BASE_DIR/ "Chroma_DB"
CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)

embedding_model = os.getenv("EMBEDDING_MODEL")

_embed_model = None


def get_embed_model() -> EmbeddingModel:
    """Returns the cached EmbeddingModel instance, instantiating it on first call."""
    global _embed_model
    if _embed_model is None:
        _embed_model = EmbeddingModel()
    return _embed_model

def __getattr__(name: str):
    """Backwards compatibility for direct retrieval.embed access."""
    if name == "embed":
        return get_embed_model()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")




class EmbeddingModel:
    """Wraps a SentenceTransformer model to embed documents and queries with task prefixes."""

    def __init__(self, model_name=embedding_model, cache_folder=str(EMBEDDINGS_MODEL_PATH)):
        """Loads the SentenceTransformer model from the local cache folder."""
        self.model = SentenceTransformer(
            model_name,
            local_files_only=False,
            trust_remote_code=False,
            cache_folder=cache_folder
        )

    def embed_documents(self, texts):
        """Adds a 'search_document' prefix to each text and returns their vector embeddings."""

        prefixed = [f"search_document: {t}" for t in texts]
        return self.model.encode(prefixed, show_progress_bar=True).tolist()

    def embed_query(self, query):
        """Adds a 'search_query' prefix to the query and returns its vector embedding."""
        
        prefixed = f"search_query: {query}"
        return self.model.encode([prefixed]).tolist()[0]
    




def generate_ids(chunks, doc_name):
    """Creates a unique string ID for each chunk using the document name, page, and chunk index."""
    ids=[]

    for i, chunk in enumerate(chunks):
        page_number = chunk["metadata"]["page_number"]
        chunk_id = f"{doc_name}_page{page_number}_chunk{i}"
        ids.append(chunk_id)

    return ids

def embed(chunks: list[dict] | str | Path, filename: str) -> None:
    """Generates embeddings for chunks and stores them in ChromaDB.
    Accepts either an in-memory list of chunk dicts or a path to a JSON chunks file."""
    embeder = EmbeddingModel()

    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
        collection = client.get_or_create_collection("my_embedded_pdfs")

        if isinstance(chunks, (str, Path)):
            with open(chunks, "r", encoding="utf-8") as f:
                chunks_list = json.load(f)
        else:
            chunks_list = chunks

        if not chunks_list:
            return

        existing_ids = set()
        try:
            existing = collection.get(where={"doc_name": filename})
            if existing and isinstance(existing.get("ids"), list):
                existing_ids = set(existing["ids"])
        except Exception:
            existing_ids = set()

        texts = [chunk["text"] for chunk in chunks_list]
        metadatas = [chunk["metadata"] for chunk in chunks_list]
        ids = generate_ids(chunks_list, filename)

        embeddings = embeder.embed_documents(texts)

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        obsolete_ids = list(existing_ids - set(ids))
        if obsolete_ids:
            collection.delete(ids=obsolete_ids)

    except FileNotFoundError as e:
        print(f"Error: Chunks file not found: {chunks}")
        raise
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in chunks file: {e}")
        raise
    except Exception as e:
        print(f"Error during embedding: {e}")
        raise

    

    
