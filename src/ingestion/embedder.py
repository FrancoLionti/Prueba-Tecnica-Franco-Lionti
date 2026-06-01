"""
Generación de embeddings usando sentence-transformers (local).

Se opta por el uso de un modelo local para generar embeddings debido a que la API no presentaba tier gratuito para este tipo de requests (Out of rate limits).

De esto se entienden los siguientes trade-offs:
- Sin costo
- Sin latencia de red
- Limitado al hardware del equipo
- Calidad de embeddings potencialmente inferior a la API

El modelo 'all-MiniLM-L6-v2' genera vectores de 384 dimensiones, es liviano (~80MB) y funciona bien para búsqueda semántica en español e inglés. Se descarga automáticamente la primera vez.

Para la generación de respuestas (LLM) sí se usa OpenAI, donde la calidad de instrucción-following importa más.
"""

from sentence_transformers import SentenceTransformer

from src.models import Chunk

_EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Carga el modelo de embeddings (lazy singleton)."""
    global _model
    if _model is None:
        _model = SentenceTransformer(_EMBEDDING_MODEL_NAME)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generador de embeddings para una lista de textos.

    Args:
        texts: Lista de textos a convertir en vectores.

    Returns:
        Lista de vectores (384 dimensiones cada uno).
    """
    model = _get_model()
    # encode devuelve arrays de numpy, luego convertidos a listas para ChromaDB
    embeddings = model.encode(texts, show_progress_bar=False)
    return [emb.tolist() for emb in embeddings]


def embed_chunks(chunks: list[Chunk]) -> list[tuple[Chunk, list[float]]]:
    """
    Genera embeddings para una lista de chunks.

    Devuelve pares (chunk, vector) para indexar en el vector store.

    Args:
        chunks: Chunks a embeber.

    Returns:
        Lista de tuplas (chunk, embedding_vector).
    """
    if not chunks:
        return []

    texts = [chunk.text for chunk in chunks]
    embeddings = embed_texts(texts)

    return list(zip(chunks, embeddings))
