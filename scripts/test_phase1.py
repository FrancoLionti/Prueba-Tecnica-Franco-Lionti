"""
Script de verificación de la Fase 1.

Lee cada documento soportado, lo normaliza, y muestra el resultado.
Esto nos permite verificar visualmente que:
- Cada reader funciona correctamente
- La normalización limpia el texto sin perder información
- La metadata se extrae correctamente
"""

from pathlib import Path

from src.config import DOCS_DIR, SUPPORTED_EXTENSIONS
from src.ingestion.readers import get_reader


def main():
    print("=" * 60)
    print("  FASE 1 — Verificación de lectura y normalización")
    print("=" * 60)

    docs_path = DOCS_DIR
    if not docs_path.exists():
        print(f"\nCarpeta de docs no encontrada: {docs_path}")
        return

    files = sorted(docs_path.iterdir())
    print(f"\nArchivos encontrados en {docs_path}:")
    for f in files:
        status = "OK" if f.suffix.lower() in SUPPORTED_EXTENSIONS else "(skip)"
        print(f"  {status} {f.name}")

    print()

    for file_path in files:
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            print(f"Saltando {file_path.name} (formato no soportado aún)")
            print("-" * 60)
            continue

        try:
            reader = get_reader(file_path)
            doc = reader.read(file_path)

            print(f" {file_path.name}")
            print(f"   Tipo: {doc.file_type}")
            print(f"   Metadata: {doc.metadata}")
            print(f"   Largo del contenido: {len(doc.content)} caracteres")
            print(f"   Preview (primeros 300 chars):")
            print(f"   ┌{'─' * 50}")
            for line in doc.content[:300].split("\n"):
                print(f"   │ {line}")
            if len(doc.content) > 300:
                print(f"   │ ...")
            print(f"   └{'─' * 50}")

        except Exception as e:
            print(f"Error leyendo {file_path.name}: {e}")

        print("-" * 60)

    print("\n Fase 1 OK.")


if __name__ == "__main__":
    main()
