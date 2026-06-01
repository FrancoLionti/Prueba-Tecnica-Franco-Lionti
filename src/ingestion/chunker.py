"""
Estrategia de fragmentación (por prioridad):
1. Cortar por doble salto de línea (separador de secciones/párrafos)
2. Si un bloque supera chunk_size, subdividirlo por oraciones
3. Agregar overlap entre chunks consecutivos para no perder contexto
   en los bordes
"""

import re

from src.config import CHUNK_OVERLAP, CHUNK_SIZE
from src.models import Chunk, Document


def chunk_document(
    doc: Document,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[Chunk]:
    """
    Divide un documento en chunks respetando límites semánticos.

    Args:
        doc: Documento normalizado a fragmentar.
        chunk_size: Tamaño máximo de cada chunk en caracteres.
        overlap: Cantidad de caracteres de superposición entre chunks.

    Returns:
        Lista de Chunks con metadata heredada del documento.
    """
    if not doc.content.strip():
        return []

    # Paso 1: separar por secciones (doble salto de línea)
    raw_sections = re.split(r"\n{2,}", doc.content)

    # Paso 2: mergear secciones cortas / subdividir las largas
    text_blocks = _fit_blocks_to_size(raw_sections, chunk_size)

    # Paso 3: aplicar overlap y construir los Chunks
    chunks = _build_chunks_with_overlap(text_blocks, overlap, doc)

    return chunks


def _fit_blocks_to_size(
    sections: list[str], max_size: int
) -> list[str]:
    """
    Ajusta los bloques de texto al tamaño deseado:
    - Fusiona secciones consecutivas cortas hasta llenar chunk_size
    - Subdivide secciones que exceden chunk_size

    Esto evita tener chunks de 50 chars (desperdicio) o de 2000 chars
    (demasiado largo para un embedding eficiente).
    """
    blocks: list[str] = []
    current_block = ""

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Si la sección sola ya excede el límite, subdividirla
        if len(section) > max_size:
            # Primero guarda lo acumulado
            if current_block:
                blocks.append(current_block)
                current_block = ""
            # Luego subdivide por oraciones
            sub_blocks = _split_by_sentences(section, max_size)
            blocks.extend(sub_blocks)
            continue

        # Si agregar esta sección excede el límite, cerrar el bloque actual
        separator = "\n\n" if current_block else ""
        if len(current_block) + len(separator) + len(section) > max_size:
            if current_block:
                blocks.append(current_block)
            current_block = section
        else:
            current_block = current_block + separator + section

    # No olvidar el último bloque
    if current_block:
        blocks.append(current_block)

    return blocks


def _split_by_sentences(text: str, max_size: int) -> list[str]:
    """
    Subdivide un texto largo cortando por oraciones completas.

    Usa puntos, signos de pregunta y exclamación como delimitadores.
    
    Si una oración sola excede max_size (poco probable), la incluye tal cual
    para no perder contenido.
    """
    # Separar por fin de oración, manteniendo el delimitador
    sentences = re.split(r"(?<=[.!?])\s+", text)

    blocks: list[str] = []
    current = ""

    for sentence in sentences:
        if not current:
            current = sentence
        elif len(current) + 1 + len(sentence) <= max_size:
            current += " " + sentence
        else:
            blocks.append(current)
            current = sentence

    if current:
        blocks.append(current)

    return blocks


def _build_chunks_with_overlap(
    blocks: list[str],
    overlap: int,
    doc: Document,
) -> list[Chunk]:
    """
    Construye los Chunks finales agregando overlap entre consecutivos.

    El overlap funciona así: los últimos N caracteres del chunk anterior
    se prependen al inicio del chunk actual. Esto asegura que si una idea
    está en el borde entre dos chunks, al menos uno la capture completa.
    """
    chunks: list[Chunk] = []

    for i, block in enumerate(blocks):
        text = block

        # Agregar overlap del bloque anterior (excepto el primero)
        if i > 0 and overlap > 0:
            prev_text = blocks[i - 1]
            # Tomar los últimos `overlap` caracteres del bloque anterior
            overlap_text = prev_text[-overlap:]
            # Intentar cortar en un espacio para no cortar palabras
            space_idx = overlap_text.find(" ")
            if space_idx > 0:
                overlap_text = overlap_text[space_idx + 1:]
            text = f"...{overlap_text} {text}"

        chunk = Chunk(
            text=text.strip(),
            source_file=doc.source_file,
            chunk_index=i,
            metadata={
                **doc.metadata,
                "total_chunks": len(blocks),
            },
            document_title=doc.metadata.get("title"),
        )
        chunks.append(chunk)

    return chunks
