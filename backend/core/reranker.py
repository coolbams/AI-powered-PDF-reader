from sentence_transformers import CrossEncoder

_model = None


def get_reranker_model() -> CrossEncoder:
    """Returns the cached CrossEncoder model, loading it on first call."""
    global _model
    if _model is None:
        _model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _model


def rerank(query: str, chunks: list[dict], top_k: int = 5) -> list[dict]:
    """Reranks the given chunks based on their relevance to the query using a cross-encoder model."""
    if not chunks:
        return []

    model = get_reranker_model()
    pairs = [(query, chunk["text"]) for chunk in chunks]

    scores = model.predict(pairs)

    for chunk, score in zip(chunks, scores):
        chunk["rerank_score"] = float(score)

    rerenked = sorted(chunks, key=lambda c: c["rerank_score"], reverse=True)
    return rerenked[:top_k]

