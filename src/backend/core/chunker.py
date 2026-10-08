from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


chunk_size = 2000
chunk_overlap = 400


def chunk_pages(pages: list[dict], doc_name: str) -> list[Document]:
    """Splits each page's text into overlapping chunks and tags them with page number and document name."""
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size = chunk_size,
        chunk_overlap = chunk_overlap,
    )

    chunks = []

    for page in pages:
        page_chunk = splitter.create_documents(
            [page["text"]]
        )

        for chunk in page_chunk:
            chunk.metadata = {
                "page_number": page["metadata"]["page_number"],
                "doc_name": doc_name,
            }

            chunks.append(chunk)
            
    return chunks