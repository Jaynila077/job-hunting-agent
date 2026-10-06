from pathlib import Path


def embed_texts(
    texts: list[str],
    model_name: str = "BAAI/bge-small-en-v1.5",
    cache_dir: Path | None = None,
) -> list[list[float]]:
    """Embeds a list of texts using fastembed, returning lists of floats."""
    if not texts:
        return []

    # Lazy import so fastembed and onnxruntime are only loaded when embedding is needed
    try:
        from fastembed import TextEmbedding
    except ImportError as exc:
        raise RuntimeError("fastembed is required for embeddings. Please install it.") from exc

    kwargs = {"model_name": model_name}
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        kwargs["cache_dir"] = str(cache_dir)

    embedding_model = TextEmbedding(**kwargs)
    embeddings = list(embedding_model.embed(texts))
    return [[round(float(v), 6) for v in emb] for emb in embeddings]