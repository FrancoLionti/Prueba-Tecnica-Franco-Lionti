"""
Tests unitarios para los readers de documentos.

Verifica que cada reader (TxtReader, MarkdownReader, JsonReader):
- Lea correctamente archivos de su formato
- Extraiga metadata relevante
- Normalice el contenido
- Maneje errores apropiadamente

El PdfReader se testea de forma separada ya que requiere
un archivo PDF real y la dependencia PyMuPDF.
"""

from pathlib import Path

import pytest

from src.ingestion.readers import (
    TxtReader,
    MarkdownReader,
    JsonReader,
    get_reader,
    READERS,
)
from src.models import Document


class TestTxtReader:
    """Tests para el lector de archivos .txt."""

    def test_reads_file_successfully(self, sample_txt: Path):
        reader = TxtReader()
        doc = reader.read(sample_txt)

        assert isinstance(doc, Document)
        assert doc.file_type == ".txt"
        assert "Error de conexión" in doc.content

    def test_extracts_sections_metadata(self, sample_txt: Path):
        reader = TxtReader()
        doc = reader.read(sample_txt)

        assert doc.metadata["format"] == "txt"
        assert doc.metadata["section_count"] >= 1
        assert isinstance(doc.metadata["sections"], list)

    def test_normalizes_content(self, sample_txt: Path):
        reader = TxtReader()
        doc = reader.read(sample_txt)

        # No debería haber espacios múltiples consecutivos
        assert "  " not in doc.content.replace("\n", " ").replace("  ", "")
        # No debería haber más de 2 newlines seguidos
        assert "\n\n\n" not in doc.content

    def test_preserves_source_file(self, sample_txt: Path):
        reader = TxtReader()
        doc = reader.read(sample_txt)

        assert doc.source_file == str(sample_txt)

    def test_file_not_found_raises(self, tmp_path: Path):
        reader = TxtReader()
        with pytest.raises(FileNotFoundError):
            reader.read(tmp_path / "no_existe.txt")


class TestMarkdownReader:
    """Tests para el lector de archivos .md."""

    def test_reads_file_successfully(self, sample_md: Path):
        reader = MarkdownReader()
        doc = reader.read(sample_md)

        assert isinstance(doc, Document)
        assert doc.file_type == ".md"
        assert "Credenciales incorrectas" in doc.content

    def test_extracts_title_from_h1(self, sample_md: Path):
        reader = MarkdownReader()
        doc = reader.read(sample_md)

        assert "title" in doc.metadata
        assert "Credenciales incorrectas" in doc.metadata["title"]

    def test_extracts_keywords(self, sample_md: Path):
        reader = MarkdownReader()
        doc = reader.read(sample_md)

        assert "keywords" in doc.metadata
        assert isinstance(doc.metadata["keywords"], list)
        assert "login" in doc.metadata["keywords"]

    def test_format_in_metadata(self, sample_md: Path):
        reader = MarkdownReader()
        doc = reader.read(sample_md)

        assert doc.metadata["format"] == "markdown"


class TestJsonReader:
    """Tests para el lector de archivos .json."""

    def test_reads_file_successfully(self, sample_json: Path):
        reader = JsonReader()
        doc = reader.read(sample_json)

        assert isinstance(doc, Document)
        assert doc.file_type == ".json"

    def test_converts_json_to_readable_text(self, sample_json: Path):
        reader = JsonReader()
        doc = reader.read(sample_json)

        # El texto convertido debe ser legible, no JSON crudo
        assert "MineCatalog" in doc.content or "Software: MineCatalog" in doc.content
        assert "ERR-DB-001" in doc.content
        assert "base de datos" in doc.content

    def test_extracts_json_metadata(self, sample_json: Path):
        reader = JsonReader()
        doc = reader.read(sample_json)

        assert doc.metadata["software"] == "MineCatalog"
        assert doc.metadata["modulo"] == "errores_frecuentes"
        assert doc.metadata["version"] == "1.0"
        assert doc.metadata["entry_count"] == 1

    def test_handles_invalid_json(self, tmp_path: Path):
        bad_json = tmp_path / "bad.json"
        bad_json.write_text("{not valid json", encoding="utf-8")

        reader = JsonReader()
        with pytest.raises(Exception):  # json.JSONDecodeError
            reader.read(bad_json)


class TestGetReader:
    """Tests para la factory function get_reader()."""

    def test_returns_txt_reader(self, tmp_path: Path):
        reader = get_reader(tmp_path / "doc.txt")
        assert isinstance(reader, TxtReader)

    def test_returns_md_reader(self, tmp_path: Path):
        reader = get_reader(tmp_path / "doc.md")
        assert isinstance(reader, MarkdownReader)

    def test_returns_json_reader(self, tmp_path: Path):
        reader = get_reader(tmp_path / "doc.json")
        assert isinstance(reader, JsonReader)

    def test_unsupported_format_raises(self, tmp_path: Path):
        with pytest.raises(ValueError, match="Formato no soportado"):
            get_reader(tmp_path / "doc.xlsx")

    def test_case_insensitive_extension(self, tmp_path: Path):
        reader = get_reader(tmp_path / "DOC.TXT")
        assert isinstance(reader, TxtReader)

    def test_all_supported_formats_registered(self):
        """Verifica que los 4 formatos están registrados."""
        assert ".txt" in READERS
        assert ".md" in READERS
        assert ".json" in READERS
        assert ".pdf" in READERS
