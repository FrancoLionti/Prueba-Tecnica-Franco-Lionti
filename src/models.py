"""
Modelos de datos compartidos para todo el sistema RAG.

Estos dataclasses son los contenedores que pasan datos entre capas:
- Document: representa un archivo leído y normalizado
- Chunk: representa un fragmento de documento listo para indexar
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Document:
    """
    Representa un documento completo después de ser leído y normalizado.

    Attributes:
        content: El texto limpio y normalizado del documento.
        source_file: Ruta al archivo original (para trazabilidad).
        file_type: Extensión del archivo (.txt, .md, .json).
        metadata: Información adicional extraída del documento
                  (ej: título, categoría, palabras clave).
    """
    content: str
    source_file: str
    file_type: str
    metadata: dict = field(default_factory=dict)

@dataclass
class Chunk:
    """
    Representa un fragmento de un documento, listo para ser embebido e indexado.

    Esto es necesario porque un documento completo puede ser demasiado largo como para enviar como contexto al LLM. Seguramente sea conveniente fragmentarlo,
    entonces se lo particiona en chunks que capturan
    una idea completa (ej: un error con su causa y solución).

    Attributes:
        text: El contenido textual del fragmento.
        source_file: Ruta al archivo original.
        chunk_index: Posición de este chunk dentro del documento (0-based).
        metadata: Metadata heredada del documento + metadata propia del chunk.
        document_title: Título del documento de origen (si se puede extraer).
    """

    text: str
    source_file: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)
    document_title: Optional[str] = None
