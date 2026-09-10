from .retrieval import Retrieval

retrive = Retrieval()

def build_prompt(query: str, chunks: list[dict]) -> str:

    context = "\n\n".join(
        f"[Source: {c['metadata']['page_number']}]\n{c['text']}"
        for c in chunks
    )

    prompt = f"""Answer the question using only the context below. 
                If the answer isn't in the context, say so.

                Context:
                {context}

                Question: {query}

                Answer:
            """
    return prompt