"""
Script de verificación de la Fase 2: Chunking.

Muestra cómo cada documento se fragmenta en chunks, con:
- Índice y tamaño de cada chunk
- Preview del contenido
- Metadata heredada
- Indicador de overlap (si aplica)
"""

from pathlib import Path

from src.config import CHUNK_OVERLAP, CHUNK_SIZE, DOCS_DIR, SUPPORTED_EXTENSIONS
from src.ingestion.chunker import chunk_document
from src.ingestion.readers import get_reader


def main():
    print("=" * 60)
    print("  FASE 2 — Verificación de Chunking")
    print(f"  chunk_size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP}")
    print("=" * 60)

    docs_path = DOCS_DIR
    total_chunks = 0

    for file_path in sorted(docs_path.iterdir()):
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        reader = get_reader(file_path)
        doc = reader.read(file_path)
        chunks = chunk_document(doc)
        total_chunks += len(chunks)

        print(f"\n{'─' * 60}")
        print(f"  {file_path.name}")
        print(f"  Documento: {len(doc.content)} chars → {len(chunks)} chunks")
        print(f"{'─' * 60}")

        for chunk in chunks:
            has_overlap = chunk.text.startswith("...")
            overlap_mark = " [+overlap]" if has_overlap else ""

            print(f"\n  Chunk #{chunk.chunk_index}{overlap_mark}")
            print(f"  Tamaño: {len(chunk.text)} chars")
            print(f"  ┌{'─' * 50}")

            # Mostrar las primeras 3 líneas del chunk
            lines = chunk.text.split("\n")
            for line in lines[:3]:
                print(f"  │ {line[:70]}")
            if len(lines) > 3:
                print(f"  │ ... ({len(lines) - 3} líneas más)")
            print(f"  └{'─' * 50}")

    print(f"\n{'=' * 60}")
    print(f"  Total: {total_chunks} chunks generados")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
