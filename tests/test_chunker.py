"""
Tests unitarios para el módulo de chunking de documentos.

Verifica que el chunker:
- Genere chunks a partir de un Document
- Respete el tamaño máximo configurado
- Aplique overlap entre chunks consecutivos
- Maneje documentos vacíos correctamente
- Preserve metadata del documento original
"""

from src.ingestion.chunker import chunk_document
from src.models import Document


class TestChunkDocument:
    """Suite de tests para chunk_document()."""

    def test_generates_chunks_from_document(self, sample_document: Document):
        """Un documento con secciones genera múltiples chunks."""
        chunks = chunk_document(sample_document, chunk_size=500, overlap=50)

        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.text.strip() != ""

    def test_empty_document_returns_no_chunks(self):
        """Un documento vacío no genera chunks."""
        empty_doc = Document(
            content="",
            source_file="empty.txt",
            file_type=".txt",
        )
        chunks = chunk_document(empty_doc)
        assert chunks == []

    def test_whitespace_only_document_returns_no_chunks(self):
        """Un documento solo con espacios no genera chunks."""
        ws_doc = Document(
            content="   \n\n  \t  ",
            source_file="ws.txt",
            file_type=".txt",
        )
        chunks = chunk_document(ws_doc)
        assert chunks == []

    def test_chunk_size_respected(self, sample_document: Document):
        """Cada chunk no excede el tamaño máximo (más el overlap)."""
        chunk_size = 200
        chunks = chunk_document(sample_document, chunk_size=chunk_size, overlap=30)

        for chunk in chunks:
            # El primer chunk no tiene overlap; los demás pueden exceder
            # ligeramente por el prefijo "..." + overlap text
            # Usamos un margen generoso para el overlap
            assert len(chunk.text) <= chunk_size + 100, (
                f"Chunk {chunk.chunk_index} excede el límite: "
                f"{len(chunk.text)} > {chunk_size + 100}"
            )

    def test_small_chunk_size_generates_more_chunks(self, sample_document: Document):
        """Un chunk_size más chico genera más chunks."""
        big_chunks = chunk_document(sample_document, chunk_size=500, overlap=0)
        small_chunks = chunk_document(sample_document, chunk_size=100, overlap=0)

        assert len(small_chunks) >= len(big_chunks)

    def test_overlap_adds_context_from_previous(self, sample_document: Document):
        """Los chunks posteriores al primero contienen texto del anterior (overlap)."""
        chunks = chunk_document(sample_document, chunk_size=150, overlap=50)

        if len(chunks) >= 2:
            # El segundo chunk debe empezar con "..." (indicador de overlap)
            assert chunks[1].text.startswith("...")

    def test_first_chunk_has_no_overlap(self, sample_document: Document):
        """El primer chunk no tiene prefijo de overlap."""
        chunks = chunk_document(sample_document, chunk_size=200, overlap=50)

        assert len(chunks) >= 1
        assert not chunks[0].text.startswith("...")

    def test_preserves_source_file(self, sample_document: Document):
        """Cada chunk hereda el source_file del documento."""
        chunks = chunk_document(sample_document, chunk_size=200, overlap=30)

        for chunk in chunks:
            assert chunk.source_file == sample_document.source_file

    def test_chunk_index_is_sequential(self, sample_document: Document):
        """Los chunk_index son secuenciales empezando en 0."""
        chunks = chunk_document(sample_document, chunk_size=200, overlap=30)

        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_metadata_includes_total_chunks(self, sample_document: Document):
        """La metadata de cada chunk incluye el total de chunks generados."""
        chunks = chunk_document(sample_document, chunk_size=200, overlap=30)

        for chunk in chunks:
            assert "total_chunks" in chunk.metadata
            assert chunk.metadata["total_chunks"] == len(chunks)

    def test_metadata_inherits_from_document(self, sample_document: Document):
        """Los chunks heredan la metadata del documento original."""
        chunks = chunk_document(sample_document, chunk_size=500, overlap=50)

        for chunk in chunks:
            assert chunk.metadata.get("format") == "txt"

    def test_zero_overlap(self, sample_document: Document):
        """Con overlap=0, ningún chunk tiene prefijo de overlap."""
        chunks = chunk_document(sample_document, chunk_size=200, overlap=0)

        for chunk in chunks:
            assert not chunk.text.startswith("...")

    def test_single_section_document(self):
        """Un documento con una sola sección genera un solo chunk."""
        doc = Document(
            content="Este es un documento corto sin separación de secciones.",
            source_file="single.txt",
            file_type=".txt",
        )
        chunks = chunk_document(doc, chunk_size=500, overlap=50)
        assert len(chunks) == 1
        assert "documento corto" in chunks[0].text
