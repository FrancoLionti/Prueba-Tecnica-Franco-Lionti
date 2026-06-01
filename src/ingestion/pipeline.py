"""
Pipeline de ingesta: orquesta el flujo completo desde archivos
hasta vectores indexados en ChromaDB.

Flujo: docs/ → read → normalize → chunk → embed (local) → store
"""

from dataclasses import dataclass
from pathlib import Path

from src.config import DOCS_DIR, SUPPORTED_EXTENSIONS
from src.ingestion.chunker import chunk_document
from src.ingestion.embedder import embed_chunks
from src.ingestion.readers import get_reader
from src.ingestion.vector_store import VectorStore
from src.models import Chunk, Document


@dataclass
class IngestionStats:
    """Estadísticas del proceso de ingesta."""
    files_processed: int
    files_skipped: int
    total_chunks: int
    total_indexed: int


def run_ingestion(
    docs_dir: str | Path | None = None,
    clear_existing: bool = True,
) -> IngestionStats:
    """
    Ejecuta el pipeline completo de ingesta.

    Args:
        docs_dir: Carpeta con los documentos. Usa DOCS_DIR por defecto.
        clear_existing: Si True, limpia los embeddings previos antes
            de re-indexar (evita duplicados).

    Returns:
        IngestionStats con métricas del proceso.
    """
    docs_path = Path(docs_dir) if docs_dir else DOCS_DIR

    if not docs_path.exists():
        raise FileNotFoundError(f"Carpeta de docs no encontrada: {docs_path}")

    # Inicializar vector store
    store = VectorStore()

    if clear_existing:
        store.clear()

    # Estadísticas
    files_processed = 0
    files_skipped = 0
    all_chunks: list[Chunk] = []

    # 1. Leer y chunkear cada documento
    for file_path in sorted(docs_path.iterdir()):
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            files_skipped += 1
            print(f"  Saltando {file_path.name} (formato no soportado)")
            continue

        try:
            reader = get_reader(file_path)
            doc: Document = reader.read(file_path)
            chunks = chunk_document(doc)
            all_chunks.extend(chunks)
            files_processed += 1
            print(f"  {file_path.name}: {len(chunks)} chunks")
        except Exception as e:
            print(f"  Error procesando {file_path.name}: {e}")
            files_skipped += 1

    if not all_chunks:
        print("  No se generaron chunks.")
        return IngestionStats(files_processed, files_skipped, 0, 0)

    # 2. Generar embeddings (localmente con sentence-transformers)
    print(f"\n  Generando embeddings para {len(all_chunks)} chunks...")
    chunk_embedding_pairs = embed_chunks(all_chunks)

    # 3. Indexar en ChromaDB
    chunks_list = [pair[0] for pair in chunk_embedding_pairs]
    embeddings_list = [pair[1] for pair in chunk_embedding_pairs]

    indexed = store.index_chunks(chunks_list, embeddings_list)
    print(f"  Indexados {indexed} chunks en ChromaDB")
    print(f"  Total en store: {store.count}")

    return IngestionStats(
        files_processed=files_processed,
        files_skipped=files_skipped,
        total_chunks=len(all_chunks),
        total_indexed=indexed,
    )


if __name__ == "__main__":
    print("=" * 50)
    print("  Pipeline de Ingesta")
    print("=" * 50)

    stats = run_ingestion()

    print(f"\n  Resultado:")
    print(f"    Archivos procesados: {stats.files_processed}")
    print(f"    Archivos saltados:   {stats.files_skipped}")
    print(f"    Chunks generados:    {stats.total_chunks}")
    print(f"    Chunks indexados:    {stats.total_indexed}")
