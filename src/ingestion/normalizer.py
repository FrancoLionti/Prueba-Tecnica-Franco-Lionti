"""
Normalización y limpieza de texto extraído de documentos.

¿Por qué normalizar?
- Los embeddings son sensibles al ruido: "Error  de   conexión" y 
  "Error de conexión" generan vectores diferentes.
- Caracteres unicode invisibles (BOM, zero-width spaces) pueden
  romper la búsqueda semántica.
- Múltiples líneas vacías consecutivas desperdician tokens sin
  aportar significado.

La normalización asegura que textos equivalentes produzcan
embeddings equivalentes.
"""

import re
import unicodedata


def normalize(text: str) -> str:
    """
    Pipeline de normalización de texto.

    Aplica las siguientes transformaciones en orden:
    1. Normalización Unicode (NFC)
    2. Eliminación de caracteres de control
    3. Colapso de whitespace
    4. Eliminación de líneas vacías excesivas
    5. Trim lead y trail

    Args:
        text: Texto crudo extraído de un documento.

    Returns:
        Texto limpio y normalizado.
    """
    if not text:
        return ""

    # 1. Normalización Unicode: convierte caracteres compuestos a su
    #    forma canónica. Ej: "é" (e + combining acute) → "é" (single char).
    #    Esto asegura que la misma letra siempre tenga la misma representación.
    text = unicodedata.normalize("NFC", text)

    # 2. Eliminar caracteres de control invisibles (excepto newlines y tabs).
    #    Estos pueden venir de copiar texto de PDFs o de editores raros.
    text = "".join(
        ch for ch in text
        if unicodedata.category(ch) != "Cc" or ch in ("\n", "\t", "\r")
    )

    # 3. Reemplazar tabs por espacios (consistencia).
    text = text.replace("\t", " ")

    # 4. Normalizar line endings: \r\n (Windows) → \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 5. Colapsar múltiples espacios en uno solo (dentro de cada línea).
    #    "Error  de   conexión" → "Error de conexión"
    text = re.sub(r"[^\S\n]+", " ", text)

    # 6. Reducir 3+ líneas vacías consecutivas a máximo 2.
    #    Preserva la separación entre secciones pero elimina excesos.
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 7. Eliminar espacios al inicio/final de cada línea.
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    # 8. Trim global.
    return text.strip()
