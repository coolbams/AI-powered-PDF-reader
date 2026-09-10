from .retrieval import Retrieval

retrive = Retrieval()

def build_prompt(query: str, chunks: list[dict]) -> str:

    context = "\n\n".join(
        f"[Source: {c['metadata']['page_number']}]\n{c['text']}"
        for c in chunks
    )

    prompt = f"""Answer ONLY using the information in the provided context. 
                Do not add information, examples, or structure that isn't explicitly stated in the context. 
                If the context doesn't cover something, say "the document doesn't specify this.

                Context:
                {context}

                Question: {query}

                Answer:
            """
    return prompt