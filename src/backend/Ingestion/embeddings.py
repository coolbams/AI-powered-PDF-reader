import json
import chromadb
from pathlib import Path
from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parent.parent

EMBEDDINGS_MODEL_PATH = BASE_DIR / "Embedding_Model"
EMBEDDINGS_MODEL_PATH.mkdir(parents=True, exist_ok=True)

CHROMA_DB_PATH = BASE_DIR/ "Chroma_DB"
CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)


class EmbeddingModel:
    def __init__(self, model_name="nomic-ai/nomic-embed-text-v1.5", cache_folder=str(EMBEDDINGS_MODEL_PATH)):
        self.model = SentenceTransformer(
            model_name,
            trust_remote_code=True,
            cache_folder=cache_folder
        )

    def embed_documents(self, texts):
        """Use this for chunks going into the vector store."""
        prefixed = [f"search_document: {t}" for t in texts]
        return self.model.encode(prefixed, show_progress_bar=True).tolist()

    def embed_query(self, query):
        """Use this for the user's question at retrieval time."""
        prefixed = f"search_query: {query}"
        return self.model.encode([prefixed]).tolist()[0]
    

embeder = EmbeddingModel()



def generate_ids(chunks, doc_name):

    ids=[]

    for i, chunk in enumerate(chunks):
        page_number = chunk["metadata"]["page_number"]
        chunk_id = f"{doc_name}_page{page_number}_chunk{i}"
        ids.append(chunk_id)

    return ids

def embed(chunk_file_path: str, filename: str) -> None:

    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
        collection = client.get_or_create_collection("my_embedded_pdfs")
    
        with open(chunk_file_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)
    
        texts = [chunk["text"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]
        ids = generate_ids(chunks, filename)
    
        embeddings = embeder.embed_documents(texts)
    
    
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        
    except  FileNotFoundError as e:
        print(f"Error: Chunks file not found: {chunk_file_path}")
        raise
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in chunks file: {e}")
        raise
    except Exception as e:
        print(f"Error during embedding: {e}")
        raise

    

    
