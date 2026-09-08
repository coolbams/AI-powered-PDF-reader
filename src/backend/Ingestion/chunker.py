from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


def chunk_pages(pages: list[dict]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size = 1000,
        chunk_overlap=200,
    )

    chunks = []

    for page in pages:
        page_chunk = splitter.create_documents(
            [page["text"]]
        )

        for chunk in page_chunk:
            chunk.metadata ={
                "page_number": page["metadata"]["page_number"]
            }

            chunks.append(chunk)
            
    return chunks