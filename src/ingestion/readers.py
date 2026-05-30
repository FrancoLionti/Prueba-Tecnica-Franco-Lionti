"""
Lectores de documentos por formato.

Patrón Strategy: una clase base abstracta define la interfaz (read),
y cada formato tiene su implementación concreta. Esto permite:
- Agregar nuevos móudlos sin modificar código existente
- Testear cada reader por separado
- Principio Open/Closed de SOLID: abierto a extensión, cerrado a modificación

El registry READERS mapea extensiones a sus readers, usado por el
pipeline para seleccionar automáticamente el reader correcto.
"""

import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Type

from src.ingestion.normalizer import normalize
from src.models import Document


class DocumentReader(ABC):
    """Interfaz base para todos los lectores de documentos."""

    @abstractmethod
    def read(self, path: Path) -> Document:
        """
        Lee un archivo y devuelve un Document normalizado.

        Args:
            path: Ruta al archivo a leer.

        Returns:
            Document con el contenido normalizado y metadata extraída.

        Raises:
            FileNotFoundError: Si el archivo no existe.
            ValueError: Si el contenido no se puede procesar.
        """
        ...


class TxtReader(DocumentReader):
    """
    Lector de archivos .txt.

    Los .txt de la documentación provista tienen un formato semi-estructurado:
    secciones numeradas (3.2, 3.3, ...) con "Mensaje mostrado", "Causas posibles"
    y "Solución". Se extrae esa estructura como metadata.
    """

    def read(self, path: Path) -> Document:
        raw = path.read_text(encoding="utf-8")
        content = normalize(raw)

        # Intentar extraer las secciones como metadata
        metadata = self._extract_sections_metadata(content)
        metadata["format"] = "txt"

        return Document(
            content=content,
            source_file=str(path),
            file_type=".txt",
            metadata=metadata,
        )

    @staticmethod
    def _extract_sections_metadata(text: str) -> dict:
        """Extrae la cantidad de secciones encontradas (útil para debugging)."""
        # Buscar patrones como "3.2 Error: ..." que indican secciones
        sections = re.findall(r"^\d+\.\d+\s+.+", text, re.MULTILINE)
        return {"section_count": len(sections), "sections": sections}


class MarkdownReader(DocumentReader):
    """
    Lector de archivos .md (Markdown).

    Los .md tienen estructura con headers (#, ##). Extraemos el título
    principal (primer H1) como metadata y preservamos la estructura
    semántica que luego el chunker puede aprovechar para cortar
    por secciones.
    """

    def read(self, path: Path) -> Document:
        raw = path.read_text(encoding="utf-8")
        content = normalize(raw)

        metadata = self._extract_md_metadata(content)
        metadata["format"] = "markdown"

        return Document(
            content=content,
            source_file=str(path),
            file_type=".md",
            metadata=metadata,
        )

    @staticmethod
    def _extract_md_metadata(text: str) -> dict:
        """Extrae título (primer H1) y keywords si existen."""
        metadata: dict = {}

        # Extraer título del primer heading H1
        h1_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if h1_match:
            metadata["title"] = h1_match.group(1).strip()

        # Buscar sección "Palabras clave" (específico de los docs de Unilink)
        kw_match = re.search(
            r"##\s+Palabras clave\s*\n(.+)", text, re.MULTILINE
        )
        if kw_match:
            keywords = [k.strip() for k in kw_match.group(1).split(",")]
            metadata["keywords"] = keywords

        return metadata


class JsonReader(DocumentReader):
    """
    Lector de archivos .json.

    Los JSON de Unilink tienen estructura específica con un array "contenido"
    de errores. Cada error tiene id, categoría, título, causas, solución
    y palabras clave.

    Convertimos la estructura JSON a texto legible porque:
    - El LLM trabaja mejor con texto natural que con JSON crudo
    - Los embeddings capturan mejor el significado en texto plano
    - Preservamos toda la información pero en formato procesable
    """

    def read(self, path: Path) -> Document:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)

        # Convertir JSON estructurado a texto legible
        content = self._json_to_text(data)
        content = normalize(content)

        metadata = self._extract_json_metadata(data)
        metadata["format"] = "json"

        return Document(
            content=content,
            source_file=str(path),
            file_type=".json",
            metadata=metadata,
        )

    @staticmethod
    def _json_to_text(data: dict) -> str:
        """
        Convierte la estructura JSON de Unilink a texto legible.

        Transforma cada entrada del array "contenido" en un bloque de texto
        con formato consistente que el LLM puede entender fácilmente.
        """
        parts: list[str] = []

        # Metadata del documento
        software = data.get("software", "")
        if software:
            parts.append(f"Software: {software}")

        modulo = data.get("modulo", "")
        if modulo:
            parts.append(f"Módulo: {modulo}")

        parts.append("")  # Línea vacía de separación

        # Contenido: cada entrada es un error documentado
        for entry in data.get("contenido", []):
            block = []
            block.append(f"ID: {entry.get('id', 'N/A')}")
            block.append(f"Categoría: {entry.get('categoria', 'N/A')}")
            block.append(f"Título: {entry.get('titulo', 'N/A')}")
            block.append(
                f"Mensaje al usuario: {entry.get('mensaje_usuario', 'N/A')}"
            )

            causas = entry.get("causas_posibles", [])
            if causas:
                block.append("Causas posibles:")
                for causa in causas:
                    block.append(f"  - {causa}")

            soluciones = entry.get("solucion", [])
            if soluciones:
                block.append("Solución:")
                for sol in soluciones:
                    block.append(f"  - {sol}")

            nivel = entry.get("nivel_soporte", "")
            if nivel:
                block.append(f"Nivel de soporte: {nivel}")

            keywords = entry.get("palabras_clave", [])
            if keywords:
                block.append(f"Palabras clave: {', '.join(keywords)}")

            parts.append("\n".join(block))

        return "\n\n".join(parts)

    @staticmethod
    def _extract_json_metadata(data: dict) -> dict:
        """Extrae metadata del nivel superior del JSON."""
        return {
            "software": data.get("software", ""),
            "modulo": data.get("modulo", ""),
            "version": data.get("version", ""),
            "entry_count": len(data.get("contenido", [])),
        }


# ── Registry ───────────────────────────────────────────────────────
# Mapea extensiones a sus readers correspondientes.
# Para agregar PDF: READERS[".pdf"] = PdfReader
READERS: dict[str, Type[DocumentReader]] = {
    ".txt": TxtReader,
    ".md": MarkdownReader,
    ".json": JsonReader,
}


def get_reader(file_path: Path) -> DocumentReader:
    """
    Factory que devuelve el reader adecuado según la extensión del archivo.

    Args:
        file_path: Ruta al archivo.

    Returns:
        Instancia del reader correspondiente.

    Raises:
        ValueError: Si la extensión no tiene un reader registrado.
    """
    ext = file_path.suffix.lower()
    reader_class = READERS.get(ext)
    if reader_class is None:
        raise ValueError(
            f"Formato no soportado: '{ext}'. "
            f"Formatos válidos: {', '.join(READERS.keys())}"
        )
    return reader_class()
