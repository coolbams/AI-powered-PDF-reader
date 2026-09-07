from langchain_text_splitters import RecursiveCharacterTextSplitter



def chunk_pages(pages):
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